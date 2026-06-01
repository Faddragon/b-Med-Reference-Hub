import json
import time
import pytest
from src.db import cache


@pytest.fixture
def cache_isolado(tmp_path, monkeypatch):
    db_path = tmp_path / "cache.sqlite"
    monkeypatch.setattr(cache, "CACHE_PATH", str(db_path))
    cache._conn = None
    cache.inicializar()
    yield
    cache._conn = None


def test_cache_vazio_retorna_none(cache_isolado):
    assert cache.get("10.1234/abc", "doi") is None


def test_cache_set_e_get(cache_isolado):
    payload = {"pmid": "1", "titulo": "X"}
    cache.set_("10.1234/abc", "doi", payload, pmid="1")
    recuperado = cache.get("10.1234/abc", "doi")
    assert recuperado == payload


def test_cache_get_tipo_errado_retorna_none(cache_isolado):
    cache.set_("chave", "doi", {"a": 1})
    assert cache.get("chave", "pmid") is None


def test_cache_atualiza_valor_existente(cache_isolado):
    cache.set_("chave", "doi", {"v": 1})
    cache.set_("chave", "doi", {"v": 2})
    assert cache.get("chave", "doi") == {"v": 2}


def test_cache_expirado_retorna_none(cache_isolado, monkeypatch):
    cache.set_("chave", "doi", {"v": 1})
    monkeypatch.setattr(cache, "CACHE_TTL_HORAS", 0)
    assert cache.get("chave", "doi") is None


def test_cache_limpar_expirados_remove_antigos(cache_isolado, monkeypatch):
    cache.set_("antigo", "doi", {"v": 1})
    cache.set_("novo", "doi", {"v": 2})
    monkeypatch.setattr(cache, "CACHE_TTL_HORAS", 0)
    removidos = cache.limpar_expirados()
    assert removidos >= 1
    assert cache.get("antigo", "doi") is None
    assert cache.get("novo", "doi") is None


def test_cache_reset_limpa_tudo(cache_isolado):
    cache.set_("a", "doi", {"v": 1})
    cache.set_("b", "pmid", {"v": 2})
    cache.reset()
    assert cache.get("a", "doi") is None
    assert cache.get("b", "pmid") is None


def test_cache_set_com_payload_complexo(cache_isolado):
    payload = {
        "pmid": "123",
        "titulo": "Ácido úrico",
        "autores": ["Silva JA", "Santos RM"],
        "ano": "2023",
        "revista": "Revista X",
        "doi": "10.1234/abc",
    }
    cache.set_("chave", "doi", payload)
    recuperado = cache.get("chave", "doi")
    assert recuperado == payload
    assert isinstance(recuperado["autores"], list)
