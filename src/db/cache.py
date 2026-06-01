import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Optional

from src.config import CACHE_PATH, CACHE_TTL_HORAS


SCHEMA = """
CREATE TABLE IF NOT EXISTS pubmed_cache (
    chave       TEXT PRIMARY KEY,
    tipo        TEXT NOT NULL,
    pmid        TEXT,
    payload     TEXT NOT NULL,
    criado_em   REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pubmed_cache_tipo ON pubmed_cache(tipo);
CREATE INDEX IF NOT EXISTS idx_pubmed_cache_pmid ON pubmed_cache(pmid);
"""


_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(CACHE_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        with _lock:
            _conn.executescript(SCHEMA)
            _conn.commit()
    return _conn


@contextmanager
def _cursor():
    conn = _get_conn()
    with _lock:
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        finally:
            cur.close()


def inicializar() -> None:
    _get_conn()


def get(chave: str, tipo: str) -> Optional[dict]:
    if not chave:
        return None
    agora = time.time()
    ttl = CACHE_TTL_HORAS * 3600
    with _cursor() as cur:
        row = cur.execute(
            "SELECT payload, criado_em FROM pubmed_cache WHERE chave = ? AND tipo = ?",
            (chave, tipo),
        ).fetchone()
    if row is None:
        return None
    if agora - row["criado_em"] >= ttl:
        return None
    return json.loads(row["payload"])


def set_(chave: str, tipo: str, payload: dict, pmid: Optional[str] = None) -> None:
    if not chave:
        return
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO pubmed_cache (chave, tipo, pmid, payload, criado_em)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chave) DO UPDATE SET
                tipo=excluded.tipo,
                pmid=excluded.pmid,
                payload=excluded.payload,
                criado_em=excluded.criado_em
            """,
            (chave, tipo, pmid, json.dumps(payload, ensure_ascii=False), time.time()),
        )


def limpar_expirados() -> int:
    ttl = CACHE_TTL_HORAS * 3600
    limite = time.time() - ttl
    with _cursor() as cur:
        cur.execute("DELETE FROM pubmed_cache WHERE criado_em <= ?", (limite,))
        return cur.rowcount


def reset() -> None:
    with _cursor() as cur:
        cur.execute("DELETE FROM pubmed_cache")
