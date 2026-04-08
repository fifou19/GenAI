"""
Centralized configuration for the HR Assistant project.
Loaded from environment variables (.env).
"""
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
MAX_RETRIES = 10      # instead of 5
BASE_WAIT = 15        # instead of 10
MAX_WAIT = 120        # instead of 60
SLEEP_BETWEEN_CALLS = 8  # instead of 4  # seconds between API calls
MAX_TOKENS = 3000  # max tokens for LLM response (to avoid very long answers)
TEMPERATURES = 0.3

# Data paths

# Clean base directory
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
CACHE_DIR = Path(os.getenv("CACHE_DIR", BASE_DIR / "cache"))

# Subfolders
GOUV_DIR = DATA_DIR / "gouv"
GOUV_MD_DIR = DATA_DIR / "gouv_md"
NOVATECH_DIR = DATA_DIR / "novatech"
NOVATECH_MD_DIR = DATA_DIR / "novatech_md"
CHAT_CACHE_DIR = CACHE_DIR / "chat_cache"
CACHE_FILE = CHAT_CACHE_DIR / "conversations.json"

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")


# Embedding
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
RERANKING_MODEL = os.getenv("RERANKING_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")

# ChromaDB
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME")

# RAG parameters

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
TOP_K = int(os.getenv("TOP_K", "5"))
DISTANCE_THRESHOLD = float(os.getenv("DISTANCE_THRESHOLD", "1.0"))
USE_RERANKING = os.getenv("USE_RERANKING", "false").lower() == "true"






def is_retryable_error(exc: Exception) -> bool:
    """ 
    Check if an API error is retryable (rate limit, server error, etc.).
    Returns True for HTTP 429, 500, 503 and related error messages.
    
    """
    status_code = getattr(exc, "status_code", None)
    if status_code in {429, 500, 503}:
        return True

    msg = str(exc).lower()
    retry_markers = [
        "429",
        "503",
        "500",
        "resource exhausted",
        "rate limit",
        "service unavailable",
        "unavailable",
        "high demand",
        "overloaded",
    ]
    return any(marker in msg for marker in retry_markers)