"""Intent resolution API - Module 4. Chat-First with JSON-LD."""

import asyncio
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from llm import resolve_intent
from db import create_intent, get_supabase
from packages.shared.utils.api_response import chat_first_response, request_id_from_request
from packages.shared.json_ld.intent import resolve_action_ld

router = APIRouter(prefix="/api/v1", tags=["Intent"])


class ResolveRequest(BaseModel):
    """Request body for intent resolution."""

    text: str = Field(..., min_length=1, max_length=2000, description="User message to resolve")
    user_id: Optional[str] = Field(None, description="Optional user ID for attribution")
    persist: bool = Field(True, description="Persist intent to database")


class ResolveResponse(BaseModel):
    """Intent resolution response - Chat-First with JSON-LD."""

    pass  # Response is dynamic dict


@router.post("/resolve")
async def resolve(
    request: Request,
    body: ResolveRequest,
):
    """
    Resolve intent from natural language.
    Uses Azure OpenAI when configured; falls back to heuristics otherwise.
    Chat-First: Returns JSON-LD and machine-readable structure for AI agents.
    """
    # Resolve intent via LLM (async to avoid blocking)
    resolved = await resolve_intent(body.text, user_id=body.user_id)

    intent_id = None
    if body.persist and get_supabase():
        try:
            intent_row = await asyncio.to_thread(
                create_intent,
                original_text=body.text,
                intent_type=resolved["intent_type"],
                entities=resolved.get("entities", []),
                graph_data={"resolved": resolved},
                confidence_score=resolved.get("confidence_score"),
                user_id=body.user_id,
            )
            intent_id = str(intent_row["id"])
        except Exception:
            pass  # Non-fatal; still return resolved intent

    request_id = request_id_from_request(request)
    machine_readable = resolve_action_ld(
        intent_type=resolved["intent_type"],
        search_query=resolved.get("search_query"),
        confidence_score=resolved.get("confidence_score"),
        entities=resolved.get("entities", []),
        intent_id=intent_id,
    )
    return chat_first_response(
        data={
            "intent_id": intent_id,
            "intent_type": resolved["intent_type"],
            "search_query": resolved.get("search_query"),
            "entities": resolved.get("entities", []),
            "confidence_score": resolved.get("confidence_score"),
        },
        machine_readable=machine_readable,
        request_id=request_id,
    )
