"""Runtime configuration. Everything comes from environment variables; no
model names, keys or endpoints are hard-coded (problem statement, Section 5)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name)
    return val if val not in (None, "") else default


LLM_MODEL = _env("LLM_MODEL")
LLM_API_KEY = _env("LLM_API_KEY")
LLM_API_BASE = _env("LLM_API_BASE")
EMBEDDING_MODEL = _env("EMBEDDING_MODEL")
LLM_TIMEOUT = float(_env("LLM_TIMEOUT", "30"))
LLM_MAX_RETRIES = int(_env("LLM_MAX_RETRIES", "2"))

DATABASE_URL = _env("DATABASE_URL", f"sqlite:///{BASE_DIR / 'buddy.db'}")
SEED_DIR = Path(_env("SEED_DIR", str(BASE_DIR.parent / "data" / "seed")))
FRONTEND_DIR = Path(_env("FRONTEND_DIR", str(BASE_DIR.parent / "frontend")))
if not FRONTEND_DIR.exists():  # inside the container
    FRONTEND_DIR = BASE_DIR / "frontend"


def llm_enabled() -> bool:
    return bool(LLM_MODEL)
