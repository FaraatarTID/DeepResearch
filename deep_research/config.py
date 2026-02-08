import os
from pathlib import Path
from dotenv import load_dotenv

# Try to import streamlit for secrets support
try:
    import streamlit as st
    _has_streamlit = True
except ImportError:
    _has_streamlit = False

# Load environment variables from .env file (fallback)
load_dotenv()

def _get_secret(key, default=None):
    """Get secret from Streamlit secrets or environment variables."""
    # First, try Streamlit secrets (if available)
    if _has_streamlit:
        try:
            if key in st.secrets:
                return st.secrets[key]
        except (FileNotFoundError, KeyError) as e:
            # Streamlit secrets access may raise depending on environment; log and fall back
            import logging
            logging.getLogger(__name__).warning("Streamlit secret access failed for %s: %s", key, e)
    
    # Fallback to environment variables
    return os.getenv(key, default)

# API Keys - prioritize Streamlit secrets, fallback to .env
GEMINI_KEY = _get_secret("GEMINI_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_MAX_DELAY_S = float(os.getenv("GEMINI_MAX_DELAY_S", 60.0))
BRAVE_API_KEY = _get_secret("BRAVE_API_KEY")
UNPAYWALL_EMAIL = _get_secret("UNPAYWALL_EMAIL")
SEMANTIC_SCHOLAR_API_KEY = _get_secret("SEMANTIC_SCHOLAR_API_KEY")

# Configuration
MAX_URLS_PER_SOURCE = int(os.getenv("MAX_URLS_PER_SOURCE", 500))
MAX_TOKENS_PER_URL = int(os.getenv("MAX_TOKENS_PER_URL", 2_000))
MAX_SNIPPETS_TO_KEEP = int(os.getenv("MAX_SNIPPETS_TO_KEEP", 100))
EST_CHAR_PER_TOKEN = 4
CONCURRENCY = int(os.getenv("CONCURRENCY", 5))  # Increased default concurrency
BRAVE_CONCURRENCY = int(os.getenv("BRAVE_CONCURRENCY", 2))
JOURNAL_H_INDEX_THRESHOLD = int(os.getenv("JOURNAL_H_INDEX_THRESHOLD", 20))
MIN_CITATION_COUNT = int(os.getenv("MIN_CITATION_COUNT", 3))  # Minimum citations for academic papers
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; DeepResearchBot/1.0)")
BRAVE_MAX_RETRIES = int(os.getenv("BRAVE_MAX_RETRIES", 3))
BRAVE_QUERY_DELAY_S = float(os.getenv("BRAVE_QUERY_DELAY_S", 0.2))
BRAVE_MAX_DELAY_S = float(os.getenv("BRAVE_MAX_DELAY_S", 4.0))
SEMANTIC_MAX_RETRIES = int(os.getenv("SEMANTIC_MAX_RETRIES", 5))
SEMANTIC_QUERY_DELAY_S = float(os.getenv("SEMANTIC_QUERY_DELAY_S", 0.4))
SEMANTIC_MAX_DELAY_S = float(os.getenv("SEMANTIC_MAX_DELAY_S", 8.0))

# Gemini rate limiting / budgeting
GEMINI_MAX_CONCURRENCY = int(os.getenv("GEMINI_MAX_CONCURRENCY", 2))
GEMINI_RPS = float(os.getenv("GEMINI_RPS", 1.0))  # requests per second
GEMINI_TOKEN_BUDGET_PER_RUN = int(os.getenv("GEMINI_TOKEN_BUDGET_PER_RUN", 20000))
GEMINI_CIRCUIT_FAILURE_THRESHOLD = int(os.getenv("GEMINI_CIRCUIT_FAILURE_THRESHOLD", 5))
GEMINI_CIRCUIT_COOLDOWN_S = float(os.getenv("GEMINI_CIRCUIT_COOLDOWN_S", 60.0))
GEMINI_ENABLE_RELEVANCE_CACHE = os.getenv("GEMINI_ENABLE_RELEVANCE_CACHE", "true").lower() in ("1", "true", "yes")

# Paths
BASE_DIR = Path(__file__).parent.parent
BIBLIO_FILE = BASE_DIR / "bibliometrics.txt"
OUTPUT_FILE = BASE_DIR / "output.docx"

def validate_config():
    """Validate that necessary configuration is present."""
    missing = []
    if not GEMINI_KEY:
        missing.append("GEMINI_KEY")
    if not BRAVE_API_KEY:
        missing.append("BRAVE_API_KEY")
    
    if missing:
        return False, f"Missing API keys: {', '.join(missing)}"
    return True, ""
