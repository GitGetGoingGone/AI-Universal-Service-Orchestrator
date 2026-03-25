"""Multi-agent registry and optional cancel hook for bundle orchestration."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from agentic.agent_registry import get_resolved_registry, registry_for_frontend

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/multi-agent", tags=["Multi-agent"])


@router.get("/agents")
async def list_agents_public():
    """
    Public agent catalog for Assistant UI (labels, skills shape, cancellable flags).
    No secrets; respects platform_config.multi_agent_config.
    """
    return registry_for_frontend()


@router.get("/registry")
async def registry_admin_shape():
    """Full resolved registry including disabled agents (for admin sync). Platform admins use Portal APIs primarily."""
    return get_resolved_registry()


class MultiAgentCancelBody(BaseModel):
    run_id: Optional[str] = Field(None, description="Reserved for future streaming runs")
    agent_id: str = Field(..., min_length=1, max_length=128)
    thread_id: Optional[str] = None


@router.post("/cancel")
async def cancel_agent_run(body: MultiAgentCancelBody):
    """
    Phase 7 placeholder: in-run cancel will use run_id + streaming.
    Today, clients send cancel_agent_ids on the next chat turn; this endpoint acknowledges intent.
    """
    reg = get_resolved_registry()
    agents_by_id = {a["id"]: a for a in reg.get("agents", [])}
    adef = agents_by_id.get(body.agent_id)
    if not adef:
        return {"ok": False, "message": "Unknown agent", "agent_id": body.agent_id}
    if not adef.get("user_cancellable"):
        return {"ok": False, "message": "Agent is not user-cancellable", "agent_id": body.agent_id}
    return {
        "ok": True,
        "message": "Add this agent id to cancel_agent_ids on your next message to skip it for that turn.",
        "agent_id": body.agent_id,
        "thread_id": body.thread_id,
    }
