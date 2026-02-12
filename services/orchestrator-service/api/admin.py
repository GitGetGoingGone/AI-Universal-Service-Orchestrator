"""Platform admin: kill switch, SLA config."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import settings
from db import get_supabase

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


class KillSwitchBody(BaseModel):
    active: bool = Field(..., description="True to activate, False to deactivate")
    reason: Optional[str] = Field(None, description="Reason for kill switch")
    activated_by: Optional[str] = Field(None, description="User ID of admin")


def _get_platform_config() -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("platform_config").select("*").limit(1).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def _update_platform_config(updates: Dict[str, Any]) -> bool:
    client = get_supabase()
    if not client:
        return False
    try:
        cfg = _get_platform_config()
        if cfg:
            client.table("platform_config").update(updates).eq("id", cfg["id"]).execute()
        else:
            client.table("platform_config").insert(updates).execute()
        return True
    except Exception:
        return False


@router.post("/kill-switch")
async def kill_switch(body: KillSwitchBody) -> Dict[str, Any]:
    """
    Activate or deactivate platform kill switch.
    When active: blocks new orders, checkout, standing intents.
    Logs to kill_switch_events.
    """
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database unavailable")

    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "kill_switch_active": body.active,
        "kill_switch_reason": body.reason,
        "kill_switch_activated_at": now if body.active else None,
        "updated_at": now,
    }
    _update_platform_config(updates)

    client.table("kill_switch_events").insert({
        "activated": body.active,
        "reason": body.reason,
        "activated_by": body.activated_by,
        "metadata": {},
    }).execute()

    return {
        "kill_switch_active": body.active,
        "reason": body.reason,
        "message": "Platform paused. New orders blocked." if body.active else "Platform resumed.",
    }


@router.get("/kill-switch")
async def get_kill_switch_status() -> Dict[str, Any]:
    """Get current kill switch status."""
    cfg = _get_platform_config()
    if not cfg:
        return {"kill_switch_active": False, "reason": None}
    return {
        "kill_switch_active": cfg.get("kill_switch_active", False),
        "reason": cfg.get("kill_switch_reason"),
        "activated_at": cfg.get("kill_switch_activated_at"),
    }


@router.get("/platform-config")
async def get_platform_config() -> Dict[str, Any]:
    """Get platform config (SLA, buffer, approval thresholds)."""
    cfg = _get_platform_config()
    if not cfg:
        return {}
    return {
        "sla_response_time_ms": cfg.get("sla_response_time_ms", 3000),
        "sla_availability_pct": float(cfg.get("sla_availability_pct", 99.5)),
        "requires_human_approval_over_cents": cfg.get("requires_human_approval_over_cents", 20000),
        "delivery_buffer_minutes": cfg.get("delivery_buffer_minutes", 15),
        "kill_switch_active": cfg.get("kill_switch_active", False),
    }


def is_kill_switch_active() -> bool:
    """Check if kill switch is active. Used by checkout, standing intents."""
    cfg = _get_platform_config()
    return bool(cfg and cfg.get("kill_switch_active"))


def get_delivery_buffer_minutes() -> int:
    """Get delivery window buffer (e.g. +15 min)."""
    cfg = _get_platform_config()
    return int(cfg.get("delivery_buffer_minutes", 15) if cfg else 15)
