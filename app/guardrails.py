"""Input guardrails: validate and normalise a request before the LLM pipeline."""

from __future__ import annotations

from .config import settings


class GuardrailError(ValueError):
    """Raised when a request fails validation."""


def validate_request(text: str) -> str:
    """Return a cleaned request string or raise GuardrailError."""
    cleaned = " ".join(text.split())  # collapse whitespace

    if len(cleaned) < settings.min_request_chars:
        raise GuardrailError(
            f"Request is too short (min {settings.min_request_chars} chars)."
        )
    if len(cleaned) > settings.max_request_chars:
        raise GuardrailError(
            f"Request is too long (max {settings.max_request_chars} chars)."
        )
    return cleaned
