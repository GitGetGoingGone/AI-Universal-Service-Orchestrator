"""Recovery trigger API - called by Omnichannel Broker on partner rejection."""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from recovery_orchestrator import handle_partner_rejection

router = APIRouter(prefix="/api/v1", tags=["Recovery"])


class TriggerBody(BaseModel):
    """Recovery trigger request from Omnichannel Broker."""

    negotiation_id: str
    rejection: Dict[str, Any]


@router.post("/recovery/trigger")
async def trigger_recovery(body: TriggerBody):
    """
    Handle partner rejection - find alternative, update bundle/order.
    Called by Omnichannel Broker when partner responds with reject.
    """
    result = await handle_partner_rejection(body.negotiation_id, body.rejection)
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result
