import time
import threading
from functools import wraps
from urllib.error import HTTPError, URLError
from socket import timeout as SocketTimeout

from src.config import (
    ENTREZ_API_KEY,
    RETRY_MAX_TENTATIVAS,
    RETRY_BACKOFF_SEGUNDOS,
)


_ENTREZ_RETRY_STATUS = {429, 500, 502, 503, 504}


class PubMedError(Exception):
    pass


class PubMedRateLimited(PubMedError):
    pass


class PubMedNotFound(PubMedError):
    pass


class PubMedNetworkError(PubMedError):
    pass


class RateLimiter:
    def __init__(self, req_por_segundo: float):
        self._intervalo = 1.0 / req_por_segundo
        self._lock = threading.Lock()
        self._ultimo = 0.0

    def aguardar(self) -> None:
        with self._lock:
            agora = time.monotonic()
            espera = self._ultimo + self._intervalo - agora
            if espera > 0:
                time.sleep(espera)
            self._ultimo = time.monotonic()


_rate_limiter = RateLimiter(10.0 if ENTREZ_API_KEY else 3.0)


def get_rate_limiter() -> RateLimiter:
    return _rate_limiter


def configurar_rate_limiter(req_por_segundo: float) -> None:
    global _rate_limiter
    _rate_limiter = RateLimiter(req_por_segundo)


def com_retry(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        ultima_excecao = None
        for tentativa in range(RETRY_MAX_TENTATIVAS):
            try:
                return fn(*args, **kwargs)
            except HTTPError as e:
                ultima_excecao = e
                if e.code not in _ENTREZ_RETRY_STATUS:
                    raise PubMedError(f"HTTP {e.code}: {e.reason}") from e
                if tentativa == RETRY_MAX_TENTATIVAS - 1:
                    raise PubMedRateLimited(
                        f"Rate limit / erro {e.code} após {RETRY_MAX_TENTATIVAS} tentativas"
                    ) from e
                espera = RETRY_BACKOFF_SEGUNDOS[tentativa]
                print(f"[retry] HTTP {e.code} - aguardando {espera}s antes de tentar de novo")
                time.sleep(espera)
            except (URLError, SocketTimeout, OSError) as e:
                ultima_excecao = e
                if tentativa == RETRY_MAX_TENTATIVAS - 1:
                    raise PubMedNetworkError(f"Falha de rede: {e}") from e
                espera = RETRY_BACKOFF_SEGUNDOS[tentativa]
                print(f"[retry] rede: {e} - aguardando {espera}s")
                time.sleep(espera)
        raise ultima_excecao

    return wrapper
