"""Standing Intent API - Module 23."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import settings
from db import get_supabase
from api.admin import is_kill_switch_active
from clients import (
    start_standing_intent_orchestration,
    raise_orchestrator_event,
    get_orchestrator_status,
)

router = APIRouter(prefix="/api/v1", tags=["Standing Intents"])


class CreateStandingIntentBody(BaseModel):
    intent_description: str = Field(..., min_length=1, max_length=2000)
    intent_conditions: Optional[Dict[str, Any]] = Field(default_factory=dict)
    user_id: Optional[str] = None
    requires_approval: bool = True
    approval_timeout_hours: int = Field(24, ge=1, le=168)
    platform: Optional[str] = None
    thread_id: Optional[str] = None


class ApproveBody(BaseModel):
    approved: bool = True
    approved_by: Optional[str] = None


@router.post("/standing-intents")
async def create_standing_intent(body: CreateStandingIntentBody) -> Dict[str, Any]:
    """Create a standing intent. Starts Durable Orchestrator and stores in DB."""
    if is_kill_switch_active():
        raise HTTPException(status_code=503, detail="Platform paused. Standing intents disabled.")
    result = await start_standing_intent_orchestration(
        message=body.intent_description,
        approval_timeout_hours=body.approval_timeout_hours,
        platform=body.platform,
        thread_id=body.thread_id,
    )
    if "error" in result:
        raise HTTPException(status_code=503, detail=result.get("error", "Orchestrator unavailable"))

    instance_id = result.get("id")
    if not instance_id:
        raise HTTPException(status_code=500, detail="No instance ID returned from orchestrator")

    client = get_supabase()
    if client:
        try:
            row = {
                "orchestration_instance_id": instance_id,
                "intent_description": body.intent_description,
                "intent_conditions": body.intent_conditions or {},
                "user_id": body.user_id,
                "requires_approval": body.requires_approval,
                "approval_timeout_hours": body.approval_timeout_hours,
                "platform": body.platform,
                "thread_id": body.thread_id,
                "status": "active",
            }
            r = client.table("standing_intents").insert(row).select().execute()
            si = r.data[0] if r.data else None
            if si:
                return {
                    "id": si["id"],
                    "orchestration_instance_id": instance_id,
                    "status": "active",
                    "status_query_uri": result.get("statusQueryGetUri"),
                }
        except Exception:
            pass

    return {
        "id": None,
        "orchestration_instance_id": instance_id,
        "status": "active",
        "status_query_uri": result.get("statusQueryGetUri"),
    }


@router.get("/standing-intents")
async def list_standing_intents(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """List standing intents."""
    client = get_supabase()
    if not client:
        return {"standing_intents": [], "count": 0}
    try:
        q = client.table("standing_intents").select("*").order("created_at", desc=True)
        if user_id:
            q = q.eq("user_id", user_id)
        if status:
            q = q.eq("status", status)
        r = q.execute()
        return {"standing_intents": r.data or [], "count": len(r.data or [])}
    except Exception:
        return {"standing_intents": [], "count": 0}


@router.get("/standing-intents/{intent_id}")
async def get_standing_intent(intent_id: str) -> Dict[str, Any]:
    """Get standing intent by ID."""
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=404, detail="Intent not found")
    try:
        r = client.table("standing_intents").select("*").eq("id", intent_id).limit(1).execute()
        si = r.data[0] if r.data else None
        if not si:
            raise HTTPException(status_code=404, detail="Intent not found")
        instance_id = si.get("orchestration_instance_id")
        if instance_id:
            status = await get_orchestrator_status(instance_id)
            si["orchestration_status"] = status
        return si
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Intent not found")


@router.post("/standing-intents/{intent_id}/approve")
async def approve_standing_intent(intent_id: str, body: ApproveBody) -> Dict[str, Any]:
    """Approve or reject standing intent. Raises UserApproval event to Durable Orchestrator."""
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=404, detail="Intent not found")
    try:
        r = client.table("standing_intents").select("*").eq("id", intent_id).limit(1).execute()
        si = r.data[0] if r.data else None
        if not si:
            raise HTTPException(status_code=404, detail="Intent not found")
        instance_id = si.get("orchestration_instance_id")
        if not instance_id:
            raise HTTPException(status_code=400, detail="No orchestration instance")
        if si.get("status") not in ("active", "pending"):
            raise HTTPException(status_code=400, detail=f"Intent in state {si.get('status')} cannot be approved")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Intent not found")

    await raise_orchestrator_event(instance_id, "UserApproval", {"approved": body.approved})

    now = datetime.now(timezone.utc).isoformat()
    if client:
        try:
            client.table("standing_intents").update({
                "status": "completed" if body.approved else "cancelled",
                "completed_at" if body.approved else "cancelled_at": now,
                "updated_at": now,
            }).eq("id", intent_id).execute()
        except Exception:
            pass

    return {"status": "approved" if body.approved else "rejected", "approved": body.approved}


@router.post("/standing-intents/{intent_id}/reject")
async def reject_standing_intent(intent_id: str) -> Dict[str, Any]:
    """Reject standing intent (alias for approve with approved=false)."""
    return await approve_standing_intent(intent_id, ApproveBody(approved=False))
