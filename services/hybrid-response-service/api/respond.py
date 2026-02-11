"""Classify-and-respond API: classify + AI response generation from KB/FAQs/order status."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import create_classification_and_respond

router = APIRouter(prefix="/api/v1", tags=["Hybrid Response"])


class ClassifyAndRespondBody(BaseModel):
    partner_id: str
    conversation_id: str
    message_content: str
    allowed_order_ids: Optional[List[str]] = None


@router.post("/classify-and-respond")
def classify_and_respond(body: ClassifyAndRespondBody) -> Dict[str, Any]:
    """
    Classify incoming message; if route=ai generate response from KB/FAQs/order status;
    if route=human create support_escalation. Order scoping: only allowed_order_ids used.
    """
    if not body.partner_id:
        raise HTTPException(status_code=400, detail="partner_id required")
    if not body.conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id required")
    if not body.message_content or not isinstance(body.message_content, str):
        raise HTTPException(status_code=400, detail="message_content required")

    return create_classification_and_respond(
        partner_id=body.partner_id,
        conversation_id=body.conversation_id,
        message_content=body.message_content.strip(),
        allowed_order_ids=body.allowed_order_ids,
    )
