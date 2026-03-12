"""Recovery trigger API - called by Omnichannel Broker on partner rejection; SLA re-sourcing."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from recovery_orchestrator import handle_partner_rejection, execute_sla_re_sourcing

router = APIRouter(prefix="/api/v1", tags=["Recovery"])


class TriggerBody(BaseModel):
    """Recovery trigger request from Omnichannel Broker."""

    negotiation_id: str
    rejection: Dict[str, Any]


class SlaExecuteBody(BaseModel):
    """Execute SLA re-sourcing: user confirmed switch to alternative."""

    experience_session_leg_id: str
    alternative_partner_id: str = Field(..., description="Partner ID for alternative")
    alternative_product_id: str = Field(..., description="Product ID for alternative")
    alternative_price: float = Field(..., description="Price for alternative")


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


@router.post("/recovery/sla-execute")
async def sla_execute(body: SlaExecuteBody):
    """
    Execute SLA re-sourcing after user confirms switch.
    Cancels old leg (external + our), adds alternative to bundle/order.
    """
    result = await execute_sla_re_sourcing(
        leg_id=body.experience_session_leg_id,
        alternative_partner_id=body.alternative_partner_id,
        alternative_product_id=body.alternative_product_id,
        alternative_price=body.alternative_price,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result
