import pytest
from src.motor_extracao.validador_doi import extrair_doi
from src.motor_extracao import pubmed_api
from src.motor_extracao import retry as retry_module
from src.db import cache as cache_module
from Bio import Entrez


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(retry_module.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(retry_module, "_rate_limiter", retry_module.RateLimiter(100000.0))


@pytest.fixture
def cache_isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "CACHE_PATH", str(tmp_path / "cache.sqlite"))
    cache_module._conn = None
    cache_module.inicializar()
    yield
    cache_module._conn = None


def test_extrair_doi_de_link_completo():
    texto = "Veja mais em https://doi.org/10.1001/jama.2023.123 e referências."
    assert extrair_doi(texto) == "10.1001/jama.2023.123"


def test_extrair_doi_puro():
    texto = "O DOI deste artigo é 10.1038/s41586-021-03819-2."
    assert extrair_doi(texto) == "10.1038/s41586-021-03819-2"


def test_extrair_doi_sem_match():
    assert extrair_doi("nenhum doi neste texto") is None


def test_extrair_doi_case_insensitive():
    texto = "HTTPS://DOI.ORG/10.1234/ABC.XYZ"
    assert extrair_doi(texto) == "10.1234/ABC.XYZ"


def test_extrair_doi_com_parenteses():
    texto = "doi:10.1234/(test).123-abc."
    assert extrair_doi(texto) == "10.1234/(test).123-abc"


def test_extrair_doi_com_ponto_e_virgula():
    texto = "10.1234/xyz; publicado em 2020."
    assert extrair_doi(texto) == "10.1234/xyz"


class FakeEsearchHandle:
    def __init__(self, id_list):
        self._id_list = id_list
    def close(self):
        pass


class FakeEfetchHandle:
    def __init__(self, records):
        self._records = records
    def close(self):
        pass


class FakeArticleId:
    def __init__(self, id_type, value):
        self.attributes = {"IdType": id_type}
        self._value = value
    def __str__(self):
        return self._value


def _make_records(pmid, titulo, ano, autores=None, doi="10.1234/test.2024.001"):
    return {
        "PubmedArticle": [
            {
                "MedlineCitation": {
                    "Article": {
                        "ArticleTitle": titulo,
                        "AuthorList": autores or [
                            {"LastName": "Doe", "Initials": "J"},
                            {"LastName": "Roe", "Initials": "A"},
                        ],
                        "Journal": {
                            "Title": "Journal of Tests",
                            "ISOAbbreviation": "J Tests",
                            "JournalIssue": {
                                "Volume": "12",
                                "Issue": "3",
                                "PubDate": {"Year": ano},
                            },
                        },
                        "Pagination": {"MedlinePgn": "10-20"},
                        "ArticleIdList": [
                            FakeArticleId("doi", doi),
                            FakeArticleId("pmc", "PMC999"),
                        ],
                    }
                }
            }
        ]
    }


def _build_mocks(monkeypatch, esearch_id_list=None, efetch_by_pmid=None):
    esearch_id_list = esearch_id_list or []
    efetch_by_pmid = efetch_by_pmid or {}

    def fake_esearch(db, term, **kwargs):
        return FakeEsearchHandle(esearch_id_list)

    def fake_efetch(db, id, retmode):
        return FakeEfetchHandle(efetch_by_pmid.get(str(id)))

    def fake_read(handle):
        if isinstance(handle, FakeEsearchHandle):
            return {"IdList": handle._id_list}
        if isinstance(handle, FakeEfetchHandle):
            return handle._records
        raise AssertionError(f"handle inesperado: {handle!r}")

    monkeypatch.setattr(Entrez, "esearch", fake_esearch)
    monkeypatch.setattr(Entrez, "efetch", fake_efetch)
    monkeypatch.setattr(Entrez, "read", fake_read)


def test_buscar_pubmed_por_doi_retorna_metadados(monkeypatch):
    _build_mocks(
        monkeypatch,
        esearch_id_list=["99999"],
        efetch_by_pmid={"99999": _make_records("99999", "A study of mock data", "2024")},
    )
    resultado = pubmed_api.buscar_pubmed_por_doi("10.1234/test.2024.001")
    assert resultado is not None
    assert resultado["pmid"] == "99999"
    assert resultado["titulo"] == "A study of mock data"
    assert resultado["autores"] == ["Doe J", "Roe A"]
    assert resultado["ano"] == "2024"
    assert resultado["revista"] == "Journal of Tests"
    assert resultado["doi"] == "10.1234/test.2024.001"


def test_buscar_pubmed_por_doi_sem_resultados(monkeypatch):
    _build_mocks(monkeypatch, esearch_id_list=[])
    assert pubmed_api.buscar_pubmed_por_doi("10.9999/nope") is None


def test_buscar_pubmed_por_doi_normaliza_chave_cache(monkeypatch, cache_isolado):
    _build_mocks(
        monkeypatch,
        esearch_id_list=["1"],
        efetch_by_pmid={"1": _make_records("1", "X", "2024")},
    )
    pubmed_api.buscar_pubmed_por_doi("10.1234/Test.2024.001")
    assert cache_module.get("10.1234/test.2024.001", "doi") is not None


def test_buscar_pubmed_por_doi_usa_cache(monkeypatch, cache_isolado):
    cache_module.set_(
        "10.1234/test.2024.001",
        "doi",
        {"pmid": "1", "titulo": "Do cache", "autores": [], "ano": "2024",
         "revista": "X", "volume": "", "numero": "", "paginas": "", "doi": "10.1234/test.2024.001"},
        pmid="1",
    )

    def must_not_call(*_a, **_k):
        raise AssertionError("API não deveria ser chamada - cache devia estar quente")

    monkeypatch.setattr(Entrez, "esearch", must_not_call)
    monkeypatch.setattr(Entrez, "efetch", must_not_call)

    resultado = pubmed_api.buscar_pubmed_por_doi("10.1234/test.2024.001")
    assert resultado["titulo"] == "Do cache"


def test_buscar_pubmed_por_pmid(monkeypatch):
    _build_mocks(
        monkeypatch,
        efetch_by_pmid={"12345": _make_records("12345", "Por PMID", "2022")},
    )
    resultado = pubmed_api.buscar_pubmed_por_pmid("12345")
    assert resultado is not None
    assert resultado["pmid"] == "12345"
    assert resultado["titulo"] == "Por PMID"


def test_buscar_pubmed_por_pmid_vazio_retorna_none(monkeypatch):
    assert pubmed_api.buscar_pubmed_por_pmid("") is None
    assert pubmed_api.buscar_pubmed_por_pmid("   ") is None


def test_buscar_pubmed_por_titulo_retorna_top_n(monkeypatch):
    _build_mocks(
        monkeypatch,
        esearch_id_list=["1", "2", "3", "4", "5"],
        efetch_by_pmid={
            "1": _make_records("1", "Artigo um", "2020"),
            "2": _make_records("2", "Artigo dois", "2021"),
            "3": _make_records("3", "Artigo tres", "2022"),
            "4": _make_records("4", "Artigo quatro", "2023"),
            "5": _make_records("5", "Artigo cinco", "2024"),
        },
    )
    resultados = pubmed_api.buscar_pubmed_por_titulo("artigo")
    assert len(resultados) == 5
    assert [r["pmid"] for r in resultados] == ["1", "2", "3", "4", "5"]


def test_buscar_pubmed_por_titulo_respeita_limite(monkeypatch):
    _build_mocks(
        monkeypatch,
        esearch_id_list=["1", "2", "3", "4", "5", "6", "7"],
        efetch_by_pmid={str(i): _make_records(str(i), f"Art {i}", "2024") for i in range(1, 8)},
    )
    resultados = pubmed_api.buscar_pubmed_por_titulo("artigo", limite=3)
    assert len(resultados) == 3


def test_buscar_pubmed_por_titulo_sem_resultados(monkeypatch):
    _build_mocks(monkeypatch, esearch_id_list=[])
    assert pubmed_api.buscar_pubmed_por_titulo("nada") == []


def test_buscar_pubmed_por_titulo_normaliza_chave_cache(monkeypatch, cache_isolado):
    _build_mocks(
        monkeypatch,
        esearch_id_list=["1"],
        efetch_by_pmid={"1": _make_records("1", "X", "2024")},
    )
    pubmed_api.buscar_pubmed_por_titulo("  Artigo  Espaçado  ")
    assert cache_module.get("artigo espaçado", "titulo") is not None


def test_buscar_pubmed_por_titulo_usa_cache(monkeypatch, cache_isolado):
    cache_module.set_(
        "artigo",
        "titulo",
        [{"pmid": "1", "titulo": "cached", "autores": [], "ano": "2024",
          "revista": "X", "volume": "", "numero": "", "paginas": "", "doi": ""}],
    )

    def must_not_call(*_a, **_k):
        raise AssertionError("API não deveria ser chamada - cache devia estar quente")

    monkeypatch.setattr(Entrez, "esearch", must_not_call)
    monkeypatch.setattr(Entrez, "efetch", must_not_call)

    resultados = pubmed_api.buscar_pubmed_por_titulo("Artigo")
    assert len(resultados) == 1
    assert resultados[0]["titulo"] == "cached"


def test_parse_records_strip_titulo_com_ponto_final(monkeypatch, cache_isolado):
    records = _make_records("1", "Sobrevivência de pacientes com carcinoma.", "2022")
    _build_mocks(
        monkeypatch,
        esearch_id_list=["1"],
        efetch_by_pmid={"1": records},
    )
    resultado = pubmed_api.buscar_pubmed_por_doi("10.1234/test.2024.001")
    assert resultado is not None
    assert not resultado["titulo"].endswith(".")
    assert resultado["titulo"] == "Sobrevivência de pacientes com carcinoma"


def test_parse_records_strip_titulo_com_pontuacao_multipla(monkeypatch, cache_isolado):
    records = _make_records("1", "Title with weird punctuation..!?::", "2022")
    _build_mocks(
        monkeypatch,
        esearch_id_list=["1"],
        efetch_by_pmid={"1": records},
    )
    resultado = pubmed_api.buscar_pubmed_por_doi("10.1234/test.2024.001")
    assert resultado["titulo"] == "Title with weird punctuation"


def test_parse_records_dedup_autores_investigadores(monkeypatch, cache_isolado):
    records = {
        "PubmedArticle": [
            {
                "MedlineCitation": {
                    "Article": {
                        "ArticleTitle": "Survival results",
                        "AuthorList": [
                            {"LastName": "Carvalho", "Initials": "GB"},
                            {"LastName": "Kohler", "Initials": "HF"},
                            {"LastName": "Lira", "Initials": "RB"},
                            {"LastName": "Vartanian", "Initials": "JG"},
                            {"LastName": "Kowalski", "Initials": "LP"},
                        ],
                        "Journal": {
                            "Title": "Brazilian journal of otorhinolaryngology",
                            "JournalIssue": {
                                "Volume": "88",
                                "Issue": "3",
                                "PubDate": {"Year": "2022"},
                            },
                        },
                        "Pagination": {"MedlinePgn": "337-344"},
                        "ArticleIdList": [FakeArticleId("doi", "10.1016/j.bjorl.2022.07.001")],
                    }
                }
            }
        ]
    }
    _build_mocks(
        monkeypatch,
        esearch_id_list=["32771434"],
        efetch_by_pmid={"32771434": records},
    )
    resultado = pubmed_api.buscar_pubmed_por_pmid("32771434")
    assert resultado is not None
    assert len(resultado["autores"]) == 5
    assert "Kowalski LP" in resultado["autores"]
    assert "Vartanian JG" in resultado["autores"]


def test_parse_records_dedup_autores_duplicados_na_lista(monkeypatch, cache_isolado):
    records = {
        "PubmedArticle": [
            {
                "MedlineCitation": {
                    "Article": {
                        "ArticleTitle": "X",
                        "AuthorList": [
                            {"LastName": "Silva", "Initials": "J"},
                            {"LastName": "Silva", "Initials": "J"},
                            {"LastName": "Santos", "Initials": "M"},
                        ],
                        "Journal": {
                            "Title": "J",
                            "JournalIssue": {
                                "Volume": "1",
                                "Issue": "1",
                                "PubDate": {"Year": "2024"},
                            },
                        },
                        "Pagination": {"MedlinePgn": "1-2"},
                        "ArticleIdList": [],
                    }
                }
            }
        ]
    }
    _build_mocks(
        monkeypatch,
        esearch_id_list=["1"],
        efetch_by_pmid={"1": records},
    )
    resultado = pubmed_api.buscar_pubmed_por_doi("10.1234/x")
    assert resultado["autores"] == ["Silva J", "Santos M"]
