"""FastAPI application for the document agent."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .agent import DocumentAgent
from .config import settings
from .guardrails import GuardrailError
from .llm import LLMError
from .models import AgentRequest, AgentResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("agent.api")

app = FastAPI(
    title="Document Agent",
    description="Generates polished Word (.docx) business documents from natural-language requests.",
    version="1.0.0",
)

# Lazy init so /health works even without an API key.
_agent: DocumentAgent | None = None


def get_agent() -> DocumentAgent:
    global _agent
    if _agent is None:
        _agent = DocumentAgent()
    return _agent


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": settings.primary_model}


@app.post("/agent", response_model=AgentResponse)
async def run_agent(payload: AgentRequest) -> AgentResponse:
    """Run the agent and return plan + document link."""
    try:
        agent = get_agent()
        return await agent.run(payload.request)
    except GuardrailError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMError as exc:
        logger.exception("LLM failure")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001  # catch-all
        logger.exception("Unexpected agent failure")
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc


@app.get("/documents/{filename}")
async def download_document(filename: str) -> FileResponse:
    """Serve a generated document. Rejects path traversal attempts."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    path = settings.output_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Document not found.")
    return FileResponse(
        path,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        filename=filename,
    )
