"""Planner: turns a user request into a structured execution plan."""

from __future__ import annotations

import logging

from .llm import LLMClient
from .models import ExecutionPlan, PlannedSection

logger = logging.getLogger("agent.planner")

_PLANNER_SYSTEM = """\
You are the planning module of an autonomous document-generation agent.
Given a user's natural-language request, decide the best structured business
document to produce and design a complete execution plan for it.

You MUST return a single JSON object with EXACTLY these keys:
{
  "document_type": string,      // e.g. "Project Plan", "Business Proposal",
                                //      "Meeting Minutes", "Technical Design",
                                //      "SOP", "Product Specification"
  "title": string,             // a specific, professional document title
  "objective": string,         // one sentence: the goal of this document
  "audience": string,          // who will read it
  "assumptions": [string],     // decisions you made where info was missing.
                               // For vague/ambiguous requests, make reasonable
                               // business assumptions and list them here.
  "sections": [                // 5-8 ordered sections; each is one task
    {
      "heading": string,       // the section heading
      "instruction": string,   // precise instruction to the writer for content
      "block_type": string     // one of: "paragraph", "bullets", "table"
    }
  ]
}

Guidelines:
- Choose section headings appropriate to the chosen document_type.
- Use "table" for structured data (timelines, budgets, roles, risk matrices).
- Use "bullets" for lists of items, deliverables, or steps.
- Use "paragraph" for narrative/explanatory prose.
- Always include an opening summary section and a closing/next-steps section.
- Return ONLY the JSON object, no prose, no markdown fences.
"""


class Planner:
    """Turns a request into a validated ExecutionPlan."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def plan(self, request: str) -> ExecutionPlan:
        user = f"User request:\n\"\"\"\n{request}\n\"\"\"\n\nProduce the execution plan JSON."
        data = await self._llm.complete_json(_PLANNER_SYSTEM, user, temperature=0.3)
        plan = self._coerce(data, request)
        logger.info(
            "Plan created: type=%s sections=%d", plan.document_type, len(plan.sections)
        )
        return plan

    @staticmethod
    def _coerce(data: dict, request: str) -> ExecutionPlan:
        """Validate and coerce LLM JSON into an ExecutionPlan."""
        raw_sections = data.get("sections") or []
        sections: list[PlannedSection] = []
        for s in raw_sections:
            if not isinstance(s, dict) or not s.get("heading"):
                continue
            bt = s.get("block_type", "paragraph")
            if bt not in ("paragraph", "bullets", "table"):
                bt = "paragraph"
            sections.append(
                PlannedSection(
                    heading=str(s["heading"]).strip(),
                    instruction=str(s.get("instruction", s["heading"])).strip(),
                    block_type=bt,
                )
            )

        if not sections:
            sections = _default_sections()

        return ExecutionPlan(
            document_type=str(data.get("document_type", "Business Report")).strip(),
            title=str(data.get("title") or _fallback_title(request)).strip(),
            objective=str(data.get("objective", "Address the user's request.")).strip(),
            audience=str(data.get("audience", "General business stakeholders")).strip(),
            assumptions=[str(a).strip() for a in (data.get("assumptions") or []) if a],
            sections=sections,
        )


def _fallback_title(request: str) -> str:
    words = request.split()
    return " ".join(words[:8]).title() or "Business Document"


def _default_sections() -> list[PlannedSection]:
    return [
        PlannedSection(heading="Executive Summary",
                       instruction="Summarise the purpose and key points.",
                       block_type="paragraph"),
        PlannedSection(heading="Background & Objectives",
                       instruction="Describe context and objectives.",
                       block_type="paragraph"),
        PlannedSection(heading="Key Details",
                       instruction="List the most important details.",
                       block_type="bullets"),
        PlannedSection(heading="Next Steps",
                       instruction="Outline recommended next actions.",
                       block_type="bullets"),
    ]
