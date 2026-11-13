"""Central settings. Everything tunable lives here and can be overridden by environment
variables (or the .env file), so the same code runs on a laptop, in CI and in a container."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    # tiny .env reader so we don't need another dependency
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if value.strip():
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    docs_dir: Path
    index_dir: Path
    log_dir: Path
    embed_backend: str        # auto | sbert | hash
    sbert_model: str
    llm_backend: str          # auto | gemini | ollama | extractive
    gemini_model: str
    gemini_api_key: str | None
    ollama_host: str
    ollama_model: str
    top_k: int
    chunk_size: int
    chunk_overlap: int
    min_dense: float          # cosine floor for the relevance gate (semantic embedders)
    min_coverage: float       # share of query terms a chunk must contain (lexical safety net)
    prompt_version: str
    api_key: str | None       # if set, the HTTP API requires an X-API-Key header
    rate_limit_per_min: int
    max_question_chars: int
    company_domain: str
    max_upload_mb: int


def _tuned_defaults() -> dict:
    """If eval/optimize_prompts.py has been run, pick up its winning config."""
    path = BASE_DIR / "eval" / "reports" / "best_config.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def load_settings() -> Settings:
    _load_dotenv(BASE_DIR / ".env")
    tuned = _tuned_defaults()
    env = os.environ.get
    return Settings(
        docs_dir=Path(env("DOCS_DIR", BASE_DIR / "data" / "docs")),
        index_dir=Path(env("INDEX_DIR", BASE_DIR / "data" / "index")),
        log_dir=Path(env("LOG_DIR", BASE_DIR / "logs")),
        embed_backend=env("EMBED_BACKEND", "auto"),
        sbert_model=env("SBERT_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        llm_backend=env("LLM_BACKEND", "auto"),
        gemini_model=env("GEMINI_MODEL", "gemini-2.5-flash"),
        gemini_api_key=env("GEMINI_API_KEY") or env("GOOGLE_API_KEY"),
        ollama_host=env("OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=env("OLLAMA_MODEL", "llama3.2"),
        top_k=int(env("TOP_K", tuned.get("top_k", 5))),
        chunk_size=int(env("CHUNK_SIZE", 800)),
        chunk_overlap=int(env("CHUNK_OVERLAP", 120)),
        min_dense=float(env("MIN_DENSE", 0.30)),
        min_coverage=float(env("MIN_COVERAGE", 0.45)),
        prompt_version=env("PROMPT_VERSION", tuned.get("prompt_version", "v2")),
        api_key=env("API_KEY"),
        rate_limit_per_min=int(env("RATE_LIMIT_PER_MIN", 30)),
        max_question_chars=int(env("MAX_QUESTION_CHARS", 1000)),
        company_domain=env("COMPANY_DOMAIN", "meridianlabs.example"),
        max_upload_mb=int(env("MAX_UPLOAD_MB", 10)),
    )
