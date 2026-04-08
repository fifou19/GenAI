"""
Configuration centralisée du projet HR Assistant.
Chargée depuis les variables d'environnement (.env)
"""

import os
from dotenv import load_dotenv

load_dotenv()
MAX_RETRIES = 10      # au lieu de 5
BASE_WAIT = 15        # au lieu de 10
MAX_WAIT = 120        # au lieu de 60
SLEEP_BETWEEN_CALLS = 8  # au lieu de 4  # seconds between API calls
MAX_TOKENS = 3000
TEMPERATURES = 0.3 # max tokens for LLM response (to avoid very long answers)
MODEL = "gemini-2.5-flash-lite"


# ============================================================
# LLM Provider — openai | anthropic | mistral | groq | gemini
# ============================================================

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# Mistral
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

# ============================================================
# Embedding (sentence-transformers, local, gratuit)
# ============================================================
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ============================================================
# ChromaDB
# ============================================================
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "hr_docs")

# ============================================================
# RAG parameters
# ============================================================
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K = int(os.getenv("TOP_K", "5"))

# ============================================================
# Data paths
# ============================================================
DATA_DIR = os.getenv("DATA_DIR", "data")
GOUV_DIR = os.path.join(DATA_DIR, "gouv")
NOVATECH_DIR = os.path.join(DATA_DIR, "novatech")
NOVATECH_MD_DIR = os.path.join(DATA_DIR, "novatech_md")



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