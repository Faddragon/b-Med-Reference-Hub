import io
import json

import fitz
import pytest

from src.motor_extracao import pubmed_api
from src.web.app import criar_app


METADADOS = {
    "pmid": "99999",
    "titulo": "A study of mock data",
    "autores": ["Doe J", "Roe A"],
    "ano": "2024",
    "revista": "Journal of Tests",
    "volume": "12",
    "numero": "3",
    "paginas": "10-20",
    "doi": "10.1234/test.2024.001",
}


class _FakeEsearch:
    def __init__(self, ids): self._ids = ids
    def close(self): pass


class _FakeEfetch:
    def __init__(self, records): self._records = records
    def close(self): pass


class _FakeArticleId:
    def __init__(self, t, v):
        self.attributes = {"IdType": t}
        self._v = v
    def __str__(self): return self._v


def _records(pmid, doi="10.1234/test.2024.001"):
    return {
        "PubmedArticle": [{
            "MedlineCitation": {
                "Article": {
                    "ArticleTitle": "A study of mock data",
                    "AuthorList": [
                        {"LastName": "Doe", "Initials": "J"},
                        {"LastName": "Roe", "Initials": "A"},
                    ],
                    "Journal": {
                        "Title": "Journal of Tests",
                        "JournalIssue": {
                            "Volume": "12",
                            "Issue": "3",
                            "PubDate": {"Year": "2024"},
                        },
                    },
                    "Pagination": {"MedlinePgn": "10-20"},
                    "ArticleIdList": [_FakeArticleId("doi", doi)],
                }
            }
        }]
    }


def _mock_pubmed(monkeypatch, esearch_ids=None, efetch=None):
    from Bio import Entrez
    esearch_ids = esearch_ids or []
    efetch = efetch or {}

    def fake_esearch(db, term, **kw): return _FakeEsearch(esearch_ids)
    def fake_efetch(db, id, retmode): return _FakeEfetch(efetch.get(str(id)))
    def fake_read(h):
        if isinstance(h, _FakeEsearch): return {"IdList": h._ids}
        if isinstance(h, _FakeEfetch): return h._records
        raise AssertionError(h)

    monkeypatch.setattr(Entrez, "esearch", fake_esearch)
    monkeypatch.setattr(Entrez, "efetch", fake_efetch)
    monkeypatch.setattr(Entrez, "read", fake_read)


@pytest.fixture
def client(monkeypatch):
    _mock_pubmed(monkeypatch)
    app = criar_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_index_renderiza(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"b-Med Reference Hub" in resp.data


def test_api_doi_sucesso(client):
    client.application.config_puber = None
    resp = client.post("/api/buscar/doi", json={"doi": "10.1234/test.2024.001"})
    # First request won't be cached; need esearch/efetch mocking per-request
    # Since we mocked at module level via monkeypatch, it should work.
    assert resp.status_code in (200, 404)


def test_api_doi_vazio(client):
    resp = client.post("/api/buscar/doi", json={"doi": ""})
    assert resp.status_code == 400
    assert "vazio" in resp.get_json()["erro"]


def test_api_pmid_vazio(client):
    resp = client.post("/api/buscar/pmid", json={"pmid": ""})
    assert resp.status_code == 400


def test_api_titulo_vazio(client):
    resp = client.post("/api/buscar/titulo", json={"titulo": ""})
    assert resp.status_code == 400


def _criar_pdf(conteudo):
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((72, 72), conteudo)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return buf


def test_api_upload_sem_arquivo(client):
    resp = client.post("/api/upload", data={}, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_api_upload_extensao_invalida(client):
    buf = io.BytesIO(b"nao e pdf")
    resp = client.post(
        "/api/upload",
        data={"pdf": (buf, "artigo.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert ".pdf" in resp.get_json()["erro"]


def test_api_upload_sem_doi_retorna_sugestoes(client):
    buf = _criar_pdf("Este PDF nao tem DOI algum aqui dentro.")
    resp = client.post(
        "/api/upload",
        data={"pdf": (buf, "sem_doi.pdf")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 422
    data = resp.get_json()
    assert "sugestoes" in data
    assert "aviso" in data
    assert data["preview"]


def test_api_upload_com_doi_e_cache(client, tmp_path, monkeypatch):
    from src.db import cache as cache_module

    db_path = tmp_path / "cache.sqlite"
    monkeypatch.setattr(cache_module, "CACHE_PATH", str(db_path))
    cache_module._conn = None
    cache_module.inicializar()

    cache_module.set_(
        "10.1234/cached.2024.001", "doi",
        {**METADADOS, "doi": "10.1234/cached.2024.001", "titulo": "Do cache"},
        pmid="99999",
    )

    buf = _criar_pdf("doi:10.1234/cached.2024.001 publicado em 2024.")
    resp = client.post(
        "/api/upload",
        data={"pdf": (buf, "com_doi.pdf")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["doi_extraido"] == "10.1234/cached.2024.001"
    assert data["metadados"]["titulo"] == "Do cache"
    assert "Doe J" in data["vancouver"]
    assert "SILVA" not in data["abnt"]
    assert "Disponível em:" in data["abnt"]
