"""Link Account API - Zero-Friction Auth (Pillar 6)."""

import hashlib
import logging
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from config import settings
from db import (
    get_supabase,
    get_user_by_clerk_id,
    get_user_by_email,
    get_account_links_by_user,
    upsert_user,
    upsert_account_link,
)
from auth.link_account import verify_google_id_token
from packages.shared.utils.api_response import chat_first_response, request_id_from_request
from packages.shared.json_ld.error import error_ld

router = APIRouter(prefix="/api/v1", tags=["Link Account"])
logger = logging.getLogger(__name__)

Provider = Literal["google", "openai"]


class LinkAccountRequest(BaseModel):
    """Request to link a platform identity to the current user."""

    provider: Provider = Field(..., description="Platform: google or openai")
    id_token: Optional[str] = Field(None, description="Google OAuth2 id_token (required for provider=google)")
    platform_user_id: Optional[str] = Field(
        None,
        description="Platform user ID (required for openai; from ChatGPT session)",
    )
    clerk_user_id: Optional[str] = Field(
        None,
        description="Clerk user ID when linking from portal (optional; used to find/create our user)",
    )


@router.post("/link-account")
async def link_account(request: Request, body: LinkAccountRequest):
    """
    Link a platform identity (Google or OpenAI/ChatGPT) to a platform user.
    - Google: send id_token from Google OAuth; we verify and store by sub. clerk_user_id optional.
    - OpenAI: send platform_user_id (from ChatGPT) + clerk_user_id (user must be signed in to link).
    """
    request_id = request_id_from_request(request)
    if not get_supabase():
        return chat_first_response(
            data={"linked": False, "error": "Database unavailable"},
            machine_readable=error_ld("Link Account unavailable: database not configured"),
            request_id=request_id,
        )

    if body.provider == "google":
        if not body.id_token:
            raise HTTPException(status_code=400, detail="id_token required for provider=google")
        client_id = getattr(settings, "google_oauth_client_id", None) or ""
        payload = verify_google_id_token(body.id_token, client_id)
        if not payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired Google id_token. Set GOOGLE_OAUTH_CLIENT_ID for verification.",
            )
        platform_user_id = payload["sub"]
        email = payload.get("email")
        display_name = payload.get("name")
        user = upsert_user(
            clerk_user_id=body.clerk_user_id,
            email=email,
            display_name=display_name,
        )
        if not user:
            raise HTTPException(status_code=503, detail="Failed to find or create user")
        user_id = str(user["id"])
        token_hash = hashlib.sha256(body.id_token.encode()).hexdigest()[:64] if body.id_token else None
        link = upsert_account_link(
            user_id=user_id,
            platform="google",
            platform_user_id=platform_user_id,
            oauth_token_hash=token_hash,
        )
        if not link:
            raise HTTPException(status_code=503, detail="Failed to save account link")
        return chat_first_response(
            data={
                "linked": True,
                "provider": "google",
                "platform_user_id": platform_user_id,
                "user_id": user_id,
            },
            machine_readable={
                "@context": "https://schema.org",
                "@type": "Thing",
                "name": "AccountLink",
                "description": "Google account linked",
                "identifier": link.get("id"),
            },
            request_id=request_id,
        )

    if body.provider == "openai":
        if not body.platform_user_id:
            raise HTTPException(status_code=400, detail="platform_user_id required for provider=openai")
        if not body.clerk_user_id:
            raise HTTPException(
                status_code=400,
                detail="clerk_user_id required for provider=openai (user must sign in to link ChatGPT)",
            )
        user = get_user_by_clerk_id(body.clerk_user_id)
        if not user:
            user = upsert_user(clerk_user_id=body.clerk_user_id)
        if not user:
            raise HTTPException(status_code=503, detail="Failed to find or create user")
        user_id = str(user["id"])
        link = upsert_account_link(
            user_id=user_id,
            platform="openai",
            platform_user_id=body.platform_user_id,
        )
        if not link:
            raise HTTPException(status_code=503, detail="Failed to save account link")
        return chat_first_response(
            data={
                "linked": True,
                "provider": "openai",
                "platform_user_id": body.platform_user_id,
                "user_id": user_id,
            },
            machine_readable={
                "@context": "https://schema.org",
                "@type": "Thing",
                "name": "AccountLink",
                "description": "OpenAI/ChatGPT account linked",
                "identifier": link.get("id"),
            },
            request_id=request_id,
        )

    raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider}")


@router.get("/link-account/status")
async def link_account_status(
    request: Request,
    user_id: Optional[str] = None,
):
    """
    Get linked platforms for a user. Pass user_id (our UUID) or ensure request is authenticated.
    """
    request_id = request_id_from_request(request)
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="user_id query parameter required (platform user UUID)",
        )
    if not get_supabase():
        return chat_first_response(
            data={"linked_platforms": []},
            machine_readable={"@context": "https://schema.org", "@type": "ItemList", "numberOfItems": 0},
            request_id=request_id,
        )
    links = get_account_links_by_user(user_id)
    linked_platforms: List[Dict[str, Any]] = [
        {"platform": l["platform"], "platform_user_id": l.get("platform_user_id"), "linked_at": l.get("created_at")}
        for l in links
    ]
    return chat_first_response(
        data={"user_id": user_id, "linked_platforms": linked_platforms},
        machine_readable={
            "@context": "https://schema.org",
            "@type": "ItemList",
            "numberOfItems": len(linked_platforms),
            "itemListElement": [
                {"@type": "Thing", "name": p["platform"], "identifier": p.get("platform_user_id")}
                for p in linked_platforms
            ],
        },
        request_id=request_id,
    )
