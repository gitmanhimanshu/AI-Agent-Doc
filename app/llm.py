"""Groq LLM client wrapper with JSON parsing, retries, and model fallback."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from groq import APIError, AsyncGroq

from .config import settings

logger = logging.getLogger("agent.llm")

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class LLMError(RuntimeError):
    """Raised when the LLM cannot produce a usable response."""


class LLMClient:
    """Thin async wrapper around the Groq chat completions API."""

    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise LLMError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        self._client = AsyncGroq(api_key=settings.groq_api_key)

    async def _raw_complete(self, model: str, messages: list[dict[str, str]],
                            temperature: float, json_mode: bool) -> str:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await self._client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    async def complete_text(self, system: str, user: str,
                            temperature: float = 0.4) -> str:
        """Return free-form text, with retry + fallback."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return await self._with_resilience(messages, temperature, json_mode=False)

    async def complete_json(self, system: str, user: str,
                            temperature: float = 0.3) -> dict[str, Any]:
        """Return parsed JSON, with retry + fallback + robust extraction."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        raw = await self._with_resilience(messages, temperature, json_mode=True)
        return self._parse_json(raw)


    async def _with_resilience(self, messages: list[dict[str, str]],
                               temperature: float, json_mode: bool) -> str:
        models = [settings.primary_model, settings.fallback_model]
        last_err: Exception | None = None
        for model in models:
            for attempt in range(1, settings.llm_max_retries + 1):
                try:
                    return await self._raw_complete(
                        model, messages, temperature, json_mode
                    )
                except APIError as exc:  # transient/provider-side failure
                    last_err = exc
                    logger.warning(
                        "LLM call failed (model=%s attempt=%s): %s",
                        model, attempt, exc,
                    )
        raise LLMError(f"All LLM attempts failed. Last error: {last_err}")

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """Best-effort JSON extraction from a model response."""
        raw = raw.strip()
        for candidate in (raw, _extract_fenced(raw), _extract_braces(raw)):
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
        raise LLMError(f"Could not parse JSON from model output: {raw[:200]}")


def _extract_fenced(text: str) -> str | None:
    m = _JSON_FENCE.search(text)
    return m.group(1) if m else None


def _extract_braces(text: str) -> str | None:
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return None
