"""Pydantic models for API, planner, and executor."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator




class AgentRequest(BaseModel):
    """Incoming payload for POST /agent."""

    request: str = Field(..., description="Natural-language request for a document.")

    @field_validator("request")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("`request` must not be empty.")
        return v.strip()




BlockType = Literal["paragraph", "bullets", "table"]


class PlannedSection(BaseModel):
    """A single section to be generated."""

    heading: str
    instruction: str = Field(..., description="What the executor should produce.")
    block_type: BlockType = "paragraph"


class ExecutionPlan(BaseModel):
    """The full plan the agent decides on before doing any work."""

    document_type: str = Field(..., description="e.g. 'Project Plan', 'Proposal'.")
    title: str
    objective: str
    audience: str = "General business stakeholders"
    assumptions: list[str] = Field(default_factory=list)
    sections: list[PlannedSection] = Field(default_factory=list)





class ContentBlock(BaseModel):
    """A renderable block of document content."""

    type: BlockType = "paragraph"
    text: str = ""
    items: list[str] = Field(default_factory=list)
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class ExecutedSection(BaseModel):
    """A section after its task has been executed."""

    heading: str
    blocks: list[ContentBlock] = Field(default_factory=list)
    status: Literal["ok", "degraded"] = "ok"


class AgentResponse(BaseModel):
    """Outgoing payload for POST /agent."""

    status: str
    message: str
    document_type: str
    title: str
    plan: ExecutionPlan
    task_list: list[str]
    warnings: list[str] = Field(default_factory=list)
    document_filename: str
    download_url: str
