"""Agent orchestrator: validate, plan, execute, render, respond."""

from __future__ import annotations

import logging
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from .document import build_document
from .executor import Executor
from .guardrails import validate_request
from .llm import LLMClient
from .models import AgentResponse, ExecutionPlan, ExecutedSection
from .planner import Planner

logger = logging.getLogger("agent.core")


class AgentState(TypedDict, total=False):
    """The state dictionary for the LangGraph workflow."""
    request: str
    clean_request: str
    plan: ExecutionPlan
    task_list: list[str]
    sections: list[ExecutedSection]
    warnings: list[str]
    document_filename: str
    status: str
    message: str


class DocumentAgent:
    """Document-generation agent using LangGraph."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()
        self._planner = Planner(self._llm)
        self._executor = Executor(self._llm)
        self._graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("validate", self._node_validate)
        workflow.add_node("plan", self._node_plan)
        workflow.add_node("execute", self._node_execute)
        workflow.add_node("render", self._node_render)
        workflow.add_node("respond", self._node_respond)

        workflow.add_edge(START, "validate")
        workflow.add_edge("validate", "plan")
        workflow.add_edge("plan", "execute")
        workflow.add_edge("execute", "render")
        workflow.add_edge("render", "respond")
        workflow.add_edge("respond", END)

        return workflow.compile()

    async def _node_validate(self, state: AgentState):
        clean_request = validate_request(state["request"])
        logger.info("Received request: %s", clean_request[:120])
        return {"clean_request": clean_request}

    async def _node_plan(self, state: AgentState):
        plan: ExecutionPlan = await self._planner.plan(state["clean_request"])
        task_list = [
            f"{i}. {s.heading} ({s.block_type})"
            for i, s in enumerate(plan.sections, start=1)
        ]
        return {"plan": plan, "task_list": task_list}

    async def _node_execute(self, state: AgentState):
        sections, warnings = await self._executor.execute(state["plan"])
        return {"sections": sections, "warnings": warnings}

    async def _node_render(self, state: AgentState):
        filename = build_document(state["plan"], state["sections"], state["clean_request"])
        return {"document_filename": filename}

    async def _node_respond(self, state: AgentState):
        degraded = sum(1 for s in state["sections"] if s.status == "degraded")
        status = "success" if degraded == 0 else "partial_success"
        message = (
            f"Generated a {state['plan'].document_type.lower()} titled '{state['plan'].title}' "
            f"with {len(state['sections'])} sections."
        )
        if degraded:
            message += f" {degraded} section(s) were degraded and need review."

        return {"status": status, "message": message}

    async def run(self, request: str) -> AgentResponse:
        initial_state = {"request": request}
        final_state = await self._graph.ainvoke(initial_state)

        return AgentResponse(
            status=final_state["status"],
            message=final_state["message"],
            document_type=final_state["plan"].document_type,
            title=final_state["plan"].title,
            plan=final_state["plan"],
            task_list=final_state["task_list"],
            warnings=final_state["warnings"],
            document_filename=final_state["document_filename"],
            download_url=f"/documents/{final_state['document_filename']}",
        )
