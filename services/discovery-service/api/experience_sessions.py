"""Experience Sessions API - user-facing and session/legs retrieval."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import (
    get_experience_session_by_thread,
    get_experience_session_legs,
    get_partner_design_chat_url,
    update_experience_session_leg_design_started,
    update_experience_session_customization_partner,
)

router = APIRouter(prefix="/api/v1", tags=["Experience Sessions"])


@router.get("/experience-sessions")
async def get_experience_session_by_thread_param(
    thread_id: str = Query(..., description="Thread ID to look up session"),
):
    """
    Get experience session by thread_id (for chat client).
    Returns session with legs embedded.
    """
    session = await get_experience_session_by_thread(thread_id)
    if not session:
        raise HTTPException(status_code=404, detail="Experience session not found")
    legs = await get_experience_session_legs(str(session["id"]))
    return {
        "data": {
            **session,
            "legs": legs,
        },
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": str(uuid.uuid4()),
        },
    }


@router.get("/experience-sessions/{session_id}")
async def get_experience_session(session_id: str):
    """Get experience session by ID with legs."""
    from db import get_experience_session_admin

    session = await get_experience_session_admin(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Experience session not found")
    return {
        "data": session,
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": str(uuid.uuid4()),
        },
    }


@router.get("/experience-sessions/{session_id}/legs")
async def get_legs(session_id: str):
    """Get legs for an experience session."""
    legs = await get_experience_session_legs(session_id)
    return {
        "data": {"legs": legs},
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": str(uuid.uuid4()),
        },
    }


class DesignStartedBody(BaseModel):
    """Partner signals design started (Point of No Return)."""

    leg_id: str


@router.post("/experience-sessions/legs/design-started")
async def design_started(body: DesignStartedBody):
    """Partner or proxy signals design started; sets allows_modification=false."""
    ok = await update_experience_session_leg_design_started(body.leg_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Leg not found")
    return {"ok": True, "leg_id": body.leg_id}


class CustomizationPartnerBody(BaseModel):
    """Set customization partner for hybrid customization."""

    session_id: str
    customization_partner_id: Optional[str] = None


@router.put("/experience-sessions/{session_id}/customization-partner")
async def set_customization_partner(session_id: str, partner_id: Optional[str] = Query(None)):
    """Set customization_partner_id (hybrid customization). Pass partner_id= to clear."""
    ok = await update_experience_session_customization_partner(session_id, partner_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True, "customization_partner_id": partner_id}


@router.put("/experience-sessions/by-thread/{thread_id}/customization-partner")
async def set_customization_partner_by_thread(thread_id: str, partner_id: Optional[str] = Query(None)):
    """Set customization_partner_id by thread_id (hybrid customization)."""
    session = await get_experience_session_by_thread(thread_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    ok = await update_experience_session_customization_partner(str(session["id"]), partner_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True, "customization_partner_id": partner_id}
