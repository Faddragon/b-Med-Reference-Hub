from Bio import Entrez

from src.config import (
    ENTREZ_EMAIL,
    ENTREZ_TOOL_NAME,
    ENTREZ_API_KEY,
    TITLE_SEARCH_LIMIT,
)
from src.db import cache
from src.motor_extracao.retry import com_retry, get_rate_limiter, PubMedError


Entrez.email = ENTREZ_EMAIL
Entrez.tool = ENTREZ_TOOL_NAME
if ENTREZ_API_KEY:
    Entrez.api_key = ENTREZ_API_KEY


CACHE_TIPO_DOI = "doi"
CACHE_TIPO_PMID = "pmid"
CACHE_TIPO_TITULO = "titulo"


def _norm_doi(doi: str) -> str:
    return (doi or "").strip().lower()


def _norm_titulo(titulo: str) -> str:
    return " ".join((titulo or "").lower().split())


def _formatar_autor(author: dict) -> tuple:
    last = author.get("LastName", "").strip()
    initials = author.get("Initials", "").strip()
    collective = author.get("CollectiveName", "").strip()
    if collective:
        return (collective.lower(), "")
    if last and initials:
        return (last.lower(), initials.lower(), f"{last} {initials}")
    if last:
        return (last.lower(), "", last)
    return None


def _dedup_autores(autores_formatados):
    vistos = set()
    resultado = []
    for tup in autores_formatados:
        if tup is None:
            continue
        chave = (tup[0], tup[1])
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(tup[2])
    return resultado


def _limpar_titulo(titulo: str) -> str:
    t = (titulo or "").strip()
    while t and t[-1] in ".!?:":
        t = t[:-1].rstrip()
    return t


def _parse_records(pmid, records):
    try:
        if not records or "PubmedArticle" not in records or len(records["PubmedArticle"]) == 0:
            return None

        article = records["PubmedArticle"][0]["MedlineCitation"]["Article"]

        titulo = _limpar_titulo(article.get("ArticleTitle", ""))

        autores = _dedup_autores(_formatar_autor(x) for x in article.get("AuthorList", []))

        journal = article.get("Journal", {})
        journal_issue = journal.get("JournalIssue", {})
        pub_date = journal_issue.get("PubDate", {})

        if "Year" in pub_date:
            ano = str(pub_date["Year"])
        elif "MedlineDate" in pub_date:
            ano = str(pub_date["MedlineDate"])[:4]
        else:
            ano = ""

        revista = journal.get("Title", "") or journal.get("ISOAbbreviation", "")

        volume = journal_issue.get("Volume", "")
        numero = journal_issue.get("Issue", "")
        paginas = article.get("Pagination", {}).get("MedlinePgn", "")

        doi = ""
        for aid in article.get("ArticleIdList", []):
            if getattr(aid, "attributes", {}).get("IdType") == "doi":
                doi = str(aid)
                break

        return {
            "pmid": str(pmid),
            "titulo": titulo,
            "autores": autores,
            "ano": ano,
            "revista": revista,
            "volume": volume,
            "numero": numero,
            "paginas": paginas,
            "doi": doi,
        }
    except (KeyError, TypeError, IndexError) as e:
        raise PubMedError(f"Resposta PubMed malformada: {e}") from e


@com_retry
def _esearch(db: str, term: str, **kwargs):
    get_rate_limiter().aguardar()
    handle = Entrez.esearch(db=db, term=term, **kwargs)
    records = Entrez.read(handle)
    handle.close()
    return records


@com_retry
def _efetch(db: str, id: str, retmode: str = "xml"):
    get_rate_limiter().aguardar()
    handle = Entrez.efetch(db=db, id=id, retmode=retmode)
    records = Entrez.read(handle)
    handle.close()
    return records


def _fetch_metadata_por_pmid(pmid: str):
    raw = _efetch(db="pubmed", id=str(pmid), retmode="xml")
    return _parse_records(pmid, raw)


def _esearch_ids(db: str, term: str) -> list:
    records = _esearch(db=db, term=term)
    return [str(x) for x in records.get("IdList", [])]


def buscar_pubmed_por_pmid(pmid: str):
    if not pmid or not str(pmid).strip():
        return None
    pmid = str(pmid).strip()
    cached = cache.get(pmid, CACHE_TIPO_PMID)
    if cached:
        return cached
    try:
        meta = _fetch_metadata_por_pmid(pmid)
    except PubMedError as e:
        print(f"[Erro PubMed PMID] {e}")
        return None
    if meta is None:
        return None
    cache.set_(pmid, CACHE_TIPO_PMID, meta, pmid=pmid)
    return meta


def buscar_pubmed_por_doi(doi: str):
    chave = _norm_doi(doi)
    if not chave:
        return None
    cached = cache.get(chave, CACHE_TIPO_DOI)
    if cached:
        return cached
    try:
        ids = _esearch_ids(db="pubmed", term=f"{doi}[doi]")
    except PubMedError as e:
        print(f"[Erro PubMed Search] {e}")
        return None
    if not ids:
        print("[!] Nenhum artigo encontrado no PubMed para este DOI.")
        return None
    pmid = ids[0]
    try:
        meta = _fetch_metadata_por_pmid(pmid)
    except PubMedError as e:
        print(f"[Erro PubMed Fetch] {e}")
        return None
    if meta is None:
        return None
    cache.set_(chave, CACHE_TIPO_DOI, meta, pmid=pmid)
    return meta


def buscar_pubmed_por_titulo(titulo: str, limite: int = TITLE_SEARCH_LIMIT):
    chave = _norm_titulo(titulo)
    if not chave:
        return []
    cached = cache.get(chave, CACHE_TIPO_TITULO)
    if cached is not None:
        return cached[:limite]
    try:
        ids = _esearch_ids(db="pubmed", term=f"{titulo}[Title]")
    except PubMedError as e:
        print(f"[Erro PubMed Search] {e}")
        return []
    if not ids:
        print("[!] Nenhum artigo encontrado no PubMed para este Título.")
        return []
    resultados = []
    for pmid in ids[:limite]:
        try:
            meta = _fetch_metadata_por_pmid(pmid)
        except PubMedError as e:
            print(f"[Erro PubMed Fetch PMID {pmid}] {e}")
            continue
        if meta is not None:
            resultados.append(meta)
    cache.set_(chave, CACHE_TIPO_TITULO, resultados)
    return resultados
