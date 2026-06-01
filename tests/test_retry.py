import time
from urllib.error import HTTPError, URLError

import pytest

from src.motor_extracao import retry


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(retry.time, "sleep", lambda *_a, **_k: None)


@pytest.fixture
def limiter_rapido(monkeypatch):
    monkeypatch.setattr(retry, "_rate_limiter", retry.RateLimiter(100000.0))
    yield


def test_rate_limiter_aguarda_intervalo(monkeypatch):
    monkeypatch.setattr(retry.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(retry.time, "monotonic", lambda: 0.0)
    rl = retry.RateLimiter(2.0)
    rl.aguardar()
    t = [0.0, 0.0, 0.1, 0.4, 0.6]
    chamadas = []
    monkeypatch.setattr(retry.time, "monotonic", lambda: t[len(chamadas) if len(chamadas) < len(t) else -1])
    for _ in range(3):
        rl.aguardar()


def _http_error(code=429):
    return HTTPError(url="http://eutils.ncbi.nlm.nih.gov", code=code, msg="Too Many Requests", hdrs={}, fp=None)


def test_com_retry_sucesso_na_primeira(monkeypatch):
    contador = {"n": 0}
    @retry.com_retry
    def fn():
        contador["n"] += 1
        return "ok"
    assert fn() == "ok"
    assert contador["n"] == 1


def test_com_retry_sucesso_apos_2_erros_429(monkeypatch):
    contador = {"n": 0}
    @retry.com_retry
    def fn():
        contador["n"] += 1
        if contador["n"] < 3:
            raise _http_error(429)
        return "ok"
    assert fn() == "ok"
    assert contador["n"] == 3


def test_com_retry_esgota_e_levanta_rate_limited(monkeypatch):
    monkeypatch.setattr(retry, "RETRY_MAX_TENTATIVAS", 3)
    @retry.com_retry
    def fn():
        raise _http_error(429)
    with pytest.raises(retry.PubMedRateLimited):
        fn()


def test_com_retry_nao_retenta_em_400(monkeypatch):
    contador = {"n": 0}
    @retry.com_retry
    def fn():
        contador["n"] += 1
        raise _http_error(400)
    with pytest.raises(retry.PubMedError):
        fn()
    assert contador["n"] == 1


def test_com_retry_retenta_em_503(monkeypatch):
    contador = {"n": 0}
    @retry.com_retry
    def fn():
        contador["n"] += 1
        if contador["n"] < 2:
            raise _http_error(503)
        return "ok"
    assert fn() == "ok"
    assert contador["n"] == 2


def test_com_retry_trata_urllib_erro(monkeypatch):
    monkeypatch.setattr(retry, "RETRY_MAX_TENTATIVAS", 2)
    @retry.com_retry
    def fn():
        raise URLError("dns falhou")
    with pytest.raises(retry.PubMedNetworkError):
        fn()


def test_com_retry_trata_socket_timeout(monkeypatch):
    from socket import timeout
    monkeypatch.setattr(retry, "RETRY_MAX_TENTATIVAS", 2)
    @retry.com_retry
    def fn():
        raise timeout("leitura")
    with pytest.raises(retry.PubMedNetworkError):
        fn()
