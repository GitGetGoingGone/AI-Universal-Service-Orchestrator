"""Chat endpoint - Agentic AI with Intent → Discovery orchestration."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from clients import resolve_intent, discover_products, start_orchestration
from agentic.loop import run_agentic_loop

router = APIRouter(prefix="/api/v1", tags=["Chat"])


class ChatRequest(BaseModel):
    """Request body for chat (natural language)."""

    text: str = Field(..., min_length=1, max_length=2000, description="User message")
    user_id: Optional[str] = Field(None, description="Optional user ID")
    limit: int = Field(20, ge=1, le=100, description="Max products when discover")


@router.post("/chat")
async def chat(
    request: Request,
    body: ChatRequest,
    agentic: bool = Query(
        True,
        description="Use agentic AI planning (LLM-based). Falls back to direct flow when disabled or LLM unavailable.",
    ),
):
    """
    AI Agents Chat Entry Point + Agentic AI.

    Single endpoint for ChatGPT/Gemini: send user message, get intent + products.
    When agentic=True (default): uses LLM to plan and execute (resolve_intent → discover_products).
    When agentic=False or LLM unavailable: direct intent→discover flow.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    # Resolve intent with user_id captured
    async def _resolve(text: str):
        return await resolve_intent(text, body.user_id)

    async def _discover(query: str, limit: int = 20, location: Optional[str] = None):
        return await discover_products(
            query=query,
            limit=limit,
            location=location,
        )

    try:
        result = await run_agentic_loop(
            body.text,
            user_id=body.user_id,
            limit=body.limit,
            resolve_intent_fn=_resolve,
            discover_products_fn=_discover,
            start_orchestration_fn=start_orchestration,
            use_agentic=agentic,
        )
    except Exception as e:
        return {
            "data": {"intent": None, "products": None, "error": str(e)},
            "machine_readable": {"@type": "Error", "description": str(e)},
            "metadata": {
                "api_version": "v1",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": request_id,
            },
        }

    if "error" in result:
        return {
            "data": {"intent": None, "products": None, "error": result["error"]},
            "machine_readable": {"@type": "Error", "description": result["error"]},
            "metadata": {
                "api_version": "v1",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": request_id,
            },
        }

    # Enrich adaptive card with agent reasoning when present
    adaptive_card = result.get("adaptive_card")
    agent_reasoning = result.get("agent_reasoning", [])
    if adaptive_card and agent_reasoning:
        reasoning_text = " • ".join(r for r in agent_reasoning if r)
        if reasoning_text:
            body = list(adaptive_card.get("body", []))
            body.insert(
                0,
                {
                    "type": "Container",
                    "style": "default",
                    "items": [
                        {"type": "TextBlock", "text": "🤔 Agent reasoning", "weight": "Bolder", "size": "Small"},
                        {"type": "TextBlock", "text": reasoning_text[:200], "size": "Small", "wrap": True},
                    ],
                },
            )
            adaptive_card = {**adaptive_card, "body": body}

    return {
        "data": result.get("data", {}),
        "machine_readable": result.get("machine_readable", {}),
        "adaptive_card": adaptive_card,
        "agent_reasoning": result.get("agent_reasoning", []),
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
        },
    }


@router.get("/agentic-consent")
async def agentic_consent():
    """
    Agentic consent and agency boundaries (per Pillar 2).
    Returns config for what the agent is allowed to do on behalf of the user.
    """
    return {
        "scope": "discover_and_browse",
        "allowed_actions": ["resolve_intent", "discover_products", "start_orchestration"],
        "requires_confirmation": ["checkout", "add_to_bundle"],
        "message": "Agent can discover products and start workflows. Checkout and add-to-bundle require user confirmation.",
    }


@router.get("/agentic-handoff")
async def agentic_handoff():
    """
    Agentic handoff config (SSO 2.0) for ChatGPT/Gemini → custom UI.
    Returns Clerk config when configured.
    """
    from config import settings

    if not settings.agentic_handoff_configured:
        return {
            "configured": False,
            "publishable_key": None,
            "sign_in_url": None,
            "message": "Configure CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY for agentic handoff.",
        }
    return {
        "configured": True,
        "publishable_key": settings.clerk_publishable_key,
        "sign_in_url": "/sign-in",
    }
