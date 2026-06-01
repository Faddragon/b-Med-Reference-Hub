import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'database.sqlite')
CACHE_PATH = os.path.join(DATA_DIR, 'cache.sqlite')
PDFS_DIR = os.path.join(DATA_DIR, 'pdfs_armazenados')

ENTREZ_EMAIL = os.getenv("BMED_ENTREZ_EMAIL", "seu_email_medico@exemplo.com")
ENTREZ_TOOL_NAME = "bMedReferenceHub"
ENTREZ_API_KEY = os.getenv("BMED_ENTREZ_API_KEY", "")

CACHE_TTL_HORAS = 24
RETRY_MAX_TENTATIVAS = 3
RETRY_BACKOFF_SEGUNDOS = (1.0, 2.0, 4.0)
TITLE_SEARCH_LIMIT = 5
TITLE_SEARCH_MIN_SCORE = 0.0

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PDFS_DIR, exist_ok=True)
