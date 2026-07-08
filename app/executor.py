"""Executor: runs planned sections concurrently and produces content blocks."""

from __future__ import annotations

import asyncio
import logging

from .llm import LLMClient, LLMError
from .models import ContentBlock, ExecutedSection, ExecutionPlan, PlannedSection

logger = logging.getLogger("agent.executor")

_WRITER_SYSTEM = """\
You are the writing module of a business document agent. You write a single
section of a larger document. Be concise, professional, and concrete. Use
realistic mock data where specifics are needed (clearly plausible, never
placeholder text like "TBD" or "lorem ipsum").

Return a single JSON object: {"blocks": [ ... ]} where each block is one of:
  {"type": "paragraph", "text": "..."}
  {"type": "bullets", "items": ["...", "..."]}
  {"type": "table", "headers": ["...","..."], "rows": [["...","..."], ...]}

Prefer the requested block_type but you may add 1-2 supporting blocks if it
improves clarity. Return ONLY the JSON object.
"""


class Executor:
    """Runs an ExecutionPlan and fills in section content."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def execute(self, plan: ExecutionPlan) -> tuple[list[ExecutedSection], list[str]]:
        """Run all section tasks concurrently. Returns (sections, warnings)."""
        results = await asyncio.gather(
            *(self._execute_section(plan, s) for s in plan.sections)
        )
        sections = [sec for sec, _ in results]
        warnings = [w for _, w in results if w]
        return sections, warnings

    async def _execute_section(
        self, plan: ExecutionPlan, section: PlannedSection
    ) -> tuple[ExecutedSection, str | None]:
        user = (
            f"Document type: {plan.document_type}\n"
            f"Document title: {plan.title}\n"
            f"Audience: {plan.audience}\n"
            f"Section heading: {section.heading}\n"
            f"Preferred block_type: {section.block_type}\n"
            f"Instruction: {section.instruction}\n\n"
            "Write this section now as the JSON described."
        )
        try:
            data = await self._llm.complete_json(_WRITER_SYSTEM, user, temperature=0.5)
            blocks = self._coerce_blocks(data)
            if not blocks:
                raise LLMError("No usable blocks returned.")
            return ExecutedSection(heading=section.heading, blocks=blocks), None
        except (LLMError, Exception) as exc:  # noqa: BLE001
            logger.warning("Section '%s' degraded: %s", section.heading, exc)
            fallback = ContentBlock(
                type="paragraph",
                text=(
                    f"[This section could not be fully generated automatically. "
                    f"Intended content: {section.instruction}]"
                ),
            )
            degraded = ExecutedSection(
                heading=section.heading, blocks=[fallback], status="degraded"
            )
            return degraded, f"Section '{section.heading}' was degraded."

    @staticmethod
    def _coerce_blocks(data: dict) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        for b in data.get("blocks", []):
            if not isinstance(b, dict):
                continue
            btype = b.get("type", "paragraph")
            if btype == "paragraph" and b.get("text"):
                blocks.append(ContentBlock(type="paragraph", text=str(b["text"]).strip()))
            elif btype == "bullets" and b.get("items"):
                items = [str(i).strip() for i in b["items"] if str(i).strip()]
                if items:
                    blocks.append(ContentBlock(type="bullets", items=items))
            elif btype == "table" and b.get("rows"):
                headers = [str(h) for h in b.get("headers", [])]
                rows = [[str(c) for c in row] for row in b["rows"] if row]
                if rows:
                    blocks.append(ContentBlock(type="table", headers=headers, rows=rows))
        return blocks
