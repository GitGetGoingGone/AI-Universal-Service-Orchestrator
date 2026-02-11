"""Hybrid Response Logic API (Module 13)."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import (
    create_classification_and_route,
    list_support_escalations,
    get_support_escalation,
    assign_escalation,
    resolve_escalation,
)

router = APIRouter(prefix="/api/v1", tags=["Hybrid Response"])


class ClassifyBody(BaseModel):
    conversation_ref: str = ""
    message_content: str = ""


class AssignBody(BaseModel):
    assigned_to: str = ""


class ResolveBody(BaseModel):
    resolution_notes: Optional[str] = None


@router.post("/classify-and-route")
def classify_and_route(body: ClassifyBody) -> Dict[str, Any]:
    """
    Classify incoming message and return route (ai | human).
    If human: creates support_escalation and returns support_escalation_id.
    """
    if not body.conversation_ref:
        raise HTTPException(status_code=400, detail="conversation_ref required")
    result = create_classification_and_route(
        conversation_ref=body.conversation_ref,
        message_content=body.message_content,
    )
    return result


@router.get("/escalations")
def list_escalations(status: Optional[str] = Query(None, description="pending | assigned | resolved")) -> Dict[str, Any]:
    escalations = list_support_escalations(status=status)
    return {"escalations": escalations, "count": len(escalations)}


@router.get("/escalations/{escalation_id}")
def get_escalation(escalation_id: str) -> Dict[str, Any]:
    esc = get_support_escalation(escalation_id)
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return esc


@router.post("/escalations/{escalation_id}/assign")
def assign_escalation_endpoint(escalation_id: str, body: AssignBody) -> Dict[str, Any]:
    if not body.assigned_to:
        raise HTTPException(status_code=400, detail="assigned_to required")
    esc = assign_escalation(escalation_id, body.assigned_to)
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return esc


@router.post("/escalations/{escalation_id}/resolve")
def resolve_escalation_endpoint(escalation_id: str, body: ResolveBody) -> Dict[str, Any]:
    esc = resolve_escalation(escalation_id, resolution_notes=body.resolution_notes)
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return esc
