"""Offline tests using a stubbed LLM (no network required)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import DocumentAgent
from app.guardrails import GuardrailError, validate_request
from app.llm import LLMClient


class StubLLM(LLMClient):
    """A fake LLM that returns canned JSON — no API key, no network."""

    def __init__(self) -> None:  # noqa: D401
        pass

    async def complete_json(self, system, user, temperature=0.3):
        if "planning module" in system:
            return {
                "document_type": "Business Report",
                "title": "Test Report",
                "objective": "Validate the pipeline.",
                "audience": "Engineers",
                "assumptions": ["Network is stubbed."],
                "sections": [
                    {"heading": "Summary", "instruction": "Summarise.",
                     "block_type": "paragraph"},
                    {"heading": "Data", "instruction": "Tabulate.",
                     "block_type": "table"},
                ],
            }
        # writer module
        return {"blocks": [{"type": "paragraph", "text": "Generated content."}]}


def test_guardrails_reject_blank() -> None:
    for bad in ("", "   ", "a"):
        try:
            validate_request(bad)
        except GuardrailError:
            continue
        raise AssertionError(f"Expected GuardrailError for {bad!r}")


def test_guardrails_collapse_whitespace() -> None:
    assert validate_request("  hello   world  ") == "hello world"


def test_end_to_end_with_stub() -> None:
    agent = DocumentAgent(llm=StubLLM())
    resp = asyncio.run(agent.run("Build a quarterly business report."))
    assert resp.status == "success"
    assert resp.title == "Test Report"
    assert len(resp.task_list) == 2
    assert resp.plan.assumptions == ["Network is stubbed."]
    assert Path("generated_docs", resp.document_filename).exists()


def test_degraded_section_still_produces_document() -> None:
    class FlakyLLM(StubLLM):
        async def complete_json(self, system, user, temperature=0.3):
            if "planning module" in system:
                return await StubLLM.complete_json(self, system, user, temperature)
            raise RuntimeError("writer boom")  # every section fails

    agent = DocumentAgent(llm=FlakyLLM())
    resp = asyncio.run(agent.run("Build a quarterly business report."))
    assert resp.status == "partial_success"
    assert resp.warnings  # degraded sections surfaced
    assert Path("generated_docs", resp.document_filename).exists()


if __name__ == "__main__":
    test_guardrails_reject_blank()
    test_guardrails_collapse_whitespace()
    test_end_to_end_with_stub()
    test_degraded_section_still_produces_document()
    print("All tests passed.")
