"""Experience Sessions API - user-facing and session/legs retrieval."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from db import (
    get_experience_session_by_thread,
    get_experience_session_legs,
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
