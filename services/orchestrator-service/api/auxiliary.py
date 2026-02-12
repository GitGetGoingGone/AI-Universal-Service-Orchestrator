"""Orchestrator auxiliary endpoints for AI agents and MCP tools.

Proxies: manifest, order status, classify-support, returns.
"""

from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings

router = APIRouter(prefix="/api/v1", tags=["Auxiliary"])


@router.get("/manifest")
async def get_manifest() -> Dict[str, Any]:
    """Proxy to discovery service manifest. AI agents discover capabilities."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{settings.discovery_service_url}/api/v1/manifest")
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Manifest unavailable")
        return r.json()


@router.get("/orders/{order_id}/status")
async def get_order_status(order_id: str) -> Dict[str, Any]:
    """Proxy to discovery service order status. Track order."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            f"{settings.discovery_service_url}/api/v1/orders/{order_id}/status"
        )
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail="Order not found")
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Order status unavailable")
        return r.json()


class ClassifySupportBody(BaseModel):
    conversation_ref: str = ""
    message_content: str = ""


@router.post("/classify-support")
async def classify_support(body: ClassifySupportBody) -> Dict[str, Any]:
    """Proxy to hybrid-response classify-and-route. Route support (AI vs human)."""
    if not body.conversation_ref:
        raise HTTPException(status_code=400, detail="conversation_ref required")
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            f"{settings.hybrid_response_service_url}/api/v1/classify-and-route",
            json={
                "conversation_ref": body.conversation_ref,
                "message_content": body.message_content,
            },
        )
        if r.status_code != 200:
            raise HTTPException(
                status_code=r.status_code,
                detail=r.json().get("detail", "Classify failed") if r.content else "Classify failed",
            )
        return r.json()


class CreateReturnBody(BaseModel):
    order_id: str
    partner_id: str
    reason: str = "other"
    reason_detail: Optional[str] = None
    order_leg_id: Optional[str] = None
    requester_id: Optional[str] = None
    photo_url: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    refund_amount_cents: Optional[int] = None


@router.post("/returns")
async def create_return(body: CreateReturnBody) -> Dict[str, Any]:
    """Proxy to reverse-logistics create return. Create return request."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            f"{settings.reverse_logistics_service_url}/api/v1/returns",
            json=body.model_dump(exclude_none=True),
        )
        if r.status_code == 500:
            raise HTTPException(status_code=500, detail="Failed to create return request")
        if r.status_code != 200:
            raise HTTPException(
                status_code=r.status_code,
                detail=r.json().get("detail", "Create return failed") if r.content else "Create return failed",
            )
        return r.json()
