"""
Central configuration for the Clinical RAG project.
Edit these values to match your team's setup — everything else
in this repo reads from here, so you only need to change it in one place.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Branding & Logging ---
PROJECT_NAME = "CareRAG"
TEAM_NAME = "Sa3ayda Geeks"
BRAND_HEADER = f"=== {PROJECT_NAME} by {TEAM_NAME} ==="

def setup_logger():
    """Initializes and returns a centralized logger for CareRAG, suppressing noisy third-party logs."""
    import logging
    logger = logging.getLogger("CareRAG")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[CareRAG - %(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    # Suppress verbose third-party loggers
    for noisy in ["chromadb", "langchain", "urllib3", "onnxruntime", "httpx"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
        
    return logger

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"
BM25_INDEX_PATH = CHROMA_DIR / "bm25_index.pkl"
SESSIONS_DIR = BASE_DIR / "sessions"
SESSION_DB_PATH = SESSIONS_DIR / "care_rag_sessions.db"
EXPORTS_DIR = SESSIONS_DIR / "exports"
COLLECTION_NAME = "clinical_guidelines"

# Ensure session directories exist
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# --- Hybrid Retrieval & Multi-Turn History ---
RRF_K_CONSTANT = 60
MAX_HISTORY_TURNS = 5



# --- Chunking ---
# Values are in approximate tokens. The splitter uses a rough
# 4-characters-per-token estimate to convert these to character counts.
CHUNK_SIZE = 400
CHUNK_OVERLAP = 50

# --- Embeddings ---
# "local"  -> free, runs on your machine, lightweight, no API key needed (default)
# "openai" -> optional, requires OPENAI_API_KEY in .env
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")
LOCAL_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# --- Retrieval ---
TOP_K = 4

# --- Generation (Gemini) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_MODEL_NAME = GEMINI_MODEL

