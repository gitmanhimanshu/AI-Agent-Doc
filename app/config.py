"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "generated_docs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    groq_api_key: str = os.getenv("GROQ_API_KEY", "")

    primary_model: str = os.getenv("PRIMARY_MODEL", "llama-3.3-70b-versatile")
    fallback_model: str = os.getenv("FALLBACK_MODEL", "llama-3.1-8b-instant")

    max_request_chars: int = int(os.getenv("MAX_REQUEST_CHARS", "4000"))
    min_request_chars: int = int(os.getenv("MIN_REQUEST_CHARS", "3"))

    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "2"))
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT", "60"))
    output_dir: Path = field(default=OUTPUT_DIR)


settings = Settings()
