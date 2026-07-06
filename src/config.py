"""Central paths, constants, and taxonomy loading.

Every other module imports from here so the whole app reads/writes
consistent locations. Keep this the single source of truth.
"""
from __future__ import annotations

import json
import os

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Paths -----------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
OUTPUTS_DIR = ROOT_DIR / "outputs"
CHROMA_DIR = DATA_DIR / "chroma"

TAXONOMY_PATH = DATA_DIR / "taxonomy.json"
STUDIES_PATH = DATA_DIR / "studies.json"
DB_PATH = DATA_DIR / "insight_engine.sqlite"
METRICS_CSV_PATH = OUTPUTS_DIR / "metrics_export.csv"

# Ensure runtime dirs exist.
for _dir in (DATA_DIR, TRANSCRIPTS_DIR, OUTPUTS_DIR, CHROMA_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# --- LLM settings ----------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None

# --- Literature search -----------------------------------------------------
# Optional, free. Without a key, Semantic Scholar still works at a lower,
# shared rate limit. Request one at https://www.semanticscholar.org/product/api
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

# Suggestions below this confidence are visually flagged for review.
LOW_CONFIDENCE_THRESHOLD = 0.6

# Embedding model used for semantic retrieval.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHROMA_COLLECTION = "insights"


# --- Taxonomy --------------------------------------------------------------
def load_taxonomy() -> dict:
    """Load the controlled tag vocabulary."""
    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def allowed_themes() -> list[str]:
    return load_taxonomy().get("themes", [])


def allowed_severities() -> list[str]:
    return load_taxonomy().get("severity", [])
