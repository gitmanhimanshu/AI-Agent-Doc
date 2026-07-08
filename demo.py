"""End-to-end demo: runs the agent on two test inputs and saves .docx files.

Usage: python demo.py
"""

from __future__ import annotations

import asyncio

from app.agent import DocumentAgent

STANDARD_REQUEST = (
    "Create a project plan for launching a company mobile app for online food "
    "ordering. Include a timeline, team roles, milestones, and a budget."
)

COMPLEX_REQUEST = (
    "We need some kind of document for the leadership offsite next month about "
    "our AI strategy. It should be a quick executive brief but also cover the "
    "technical roadmap in detail, mention budget (we don't have exact numbers "
    "yet), and it must fit on one page but be comprehensive. Figure out the "
    "best structure yourself."
)


async def _run_one(agent: DocumentAgent, label: str, request: str) -> None:
    print("\n" + "=" * 78)
    print(f"{label}\nRequest: {request}")
    print("=" * 78)
    resp = await agent.run(request)

    print(f"\nStatus         : {resp.status}")
    print(f"Document type  : {resp.document_type}")
    print(f"Title          : {resp.title}")
    print(f"Objective      : {resp.plan.objective}")
    if resp.plan.assumptions:
        print("\nAssumptions the agent made:")
        for a in resp.plan.assumptions:
            print(f"   - {a}")
    print("\nAgent-generated task list:")
    for task in resp.task_list:
        print(f"   {task}")
    if resp.warnings:
        print("\nWarnings:")
        for w in resp.warnings:
            print(f"   ! {w}")
    print(f"\nMessage        : {resp.message}")
    print(f"Saved document : generated_docs/{resp.document_filename}")


async def main() -> None:
    agent = DocumentAgent()
    await _run_one(agent, "TEST 1 — STANDARD BUSINESS REQUEST", STANDARD_REQUEST)
    await _run_one(agent, "TEST 2 — COMPLEX / AMBIGUOUS REQUEST", COMPLEX_REQUEST)
    print("\nDone. Open the .docx files in the generated_docs/ folder.\n")


if __name__ == "__main__":
    asyncio.run(main())
