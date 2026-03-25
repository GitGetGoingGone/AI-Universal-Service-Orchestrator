"""Multi-agent bundle orchestration: AgentInvocation, AgentResult, PAO trace (Plan–Action–Observe)."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

AgentPhase = Literal["PLAN", "ACTION", "OBSERVE"]
AgentStatus = Literal["pending", "running", "succeeded", "failed", "cancelled"]
AgentKind = Literal["discovery", "context", "resourcing", "integration"]


class AgentOperation(BaseModel):
    """Single PAO step; ACTION labels must be human-readable (no raw URLs)."""

    phase: AgentPhase
    label: str = Field(..., min_length=1, max_length=500)
    timestamp: Optional[float] = Field(None, description="Unix epoch seconds")
    detail: Optional[str] = Field(None, max_length=2000)


class AgentInvocation(BaseModel):
    """Input to a bundle scout agent."""

    agent_id: str
    user_message: str
    intent: Dict[str, Any] = Field(default_factory=dict)
    thread_id: Optional[str] = None
    user_id: Optional[str] = None
    location: Optional[str] = None
    time_window: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)
    skills: Dict[str, Any] = Field(default_factory=dict, description="Merged admin + user skills")


class OperationProgress(BaseModel):
    """Fine-grained sub-step for huddle UI."""

    label: str
    status: Literal["pending", "in_progress", "done", "failed"] = "pending"


class AgentResult(BaseModel):
    """Outcome of one agent run for multi_agent_status."""

    id: str
    label: str
    kind: AgentKind = "discovery"
    status: AgentStatus = "pending"
    summary: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)
    operations: List[OperationProgress] = Field(default_factory=list)
    trace: List[AgentOperation] = Field(default_factory=list)
    user_cancellable: bool = False
    user_editable: bool = False

    def model_dump_public(self) -> Dict[str, Any]:
        d = self.model_dump(mode="json")
        return d


def trace_append(
    trace: List[AgentOperation],
    phase: AgentPhase,
    label: str,
    detail: Optional[str] = None,
) -> None:
    trace.append(
        AgentOperation(
            phase=phase,
            label=label,
            timestamp=time.time(),
            detail=detail,
        )
    )
