"""Authentication for Partner Portal."""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from config import settings
from db import get_partner_by_id, is_partner_admin, is_partner_owner, is_platform_admin, verify_api_key

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
BEARER = HTTPBearer(auto_error=False)


async def _verify_clerk_token(token: str) -> Optional[dict]:
    """Verify Clerk JWT and return user payload. Returns None if Clerk not configured."""
    if not settings.clerk_secret_key:
        return None
    try:
        import jwt
        decoded = jwt.decode(
            token,
            settings.clerk_secret_key,
            algorithms=["HS256", "RS256"],
            options={"verify_aud": False},
        )
        return decoded
    except Exception as e:
        logger.warning("Clerk JWT verify failed: %s", e)
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(BEARER),
    x_api_key: Optional[str] = Security(API_KEY_HEADER),
) -> Optional[dict]:
    """
    Resolve current user from Bearer token (Clerk JWT) or request.state.
    Returns None if no auth (dev/demo mode).
    """
    # Check if already set by middleware
    if hasattr(request.state, "user") and request.state.user:
        return request.state.user

    # Try Bearer token (Clerk JWT)
    if credentials and credentials.credentials:
        user = await _verify_clerk_token(credentials.credentials)
        if user:
            return {"id": user.get("sub"), "email": user.get("email")}

    # Try API key
    if x_api_key:
        partner_id = await verify_api_key(x_api_key)
        if partner_id:
            return {"id": f"api:{partner_id}", "partner_id": partner_id}

    return None


async def require_partner_admin(partner_id: str, request: Request) -> str:
    """
    Ensure caller has admin access to the given partner_id.
    Raises 401/403 if auth required and not satisfied.
    When auth not required: always returns partner_id (dev/demo).
    """
    if not settings.auth_required:
        return partner_id

    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = user.get("id")
    if user_id and user_id.startswith("api:"):
        # API key auth - partner_id must match
        if user.get("partner_id") == partner_id:
            return partner_id
        raise HTTPException(status_code=403, detail="API key does not match partner")

    if await is_platform_admin(user_id):
        return partner_id
    if await is_partner_admin(user_id, partner_id):
        return partner_id

    raise HTTPException(status_code=403, detail="Admin access required")


async def require_partner_owner(partner_id: str, request: Request) -> str:
    """Ensure caller is partner owner. For promote/revoke admin."""
    if not settings.auth_required:
        return partner_id

    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = user.get("id")
    if user_id and user_id.startswith("api:"):
        raise HTTPException(status_code=403, detail="Owner access required")

    if await is_platform_admin(user_id):
        return partner_id
    if await is_partner_owner(user_id, partner_id):
        return partner_id

    raise HTTPException(status_code=403, detail="Owner access required")


async def require_platform_admin(request: Request) -> str:
    """Ensure caller is platform admin. Raises 401/403 if not."""
    if not settings.auth_required:
        return "platform"

    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = user.get("id")
    if user_id and user_id.startswith("api:"):
        raise HTTPException(status_code=403, detail="Platform admin required")

    if await is_platform_admin(user_id):
        return "platform"

    raise HTTPException(status_code=403, detail="Platform admin required")


async def get_partner_from_api_key(
    x_api_key: Optional[str] = Security(API_KEY_HEADER),
) -> Optional[str]:
    """
    Resolve partner_id from X-API-Key header.
    Returns partner_id if valid, None if key not provided (and auth not required).
    """
    if not x_api_key:
        return None
    partner_id = await verify_api_key(x_api_key)
    return partner_id


async def require_partner_access(
    partner_id: str,
    x_api_key: Optional[str] = Security(API_KEY_HEADER),
) -> str:
    """
    Ensure caller has access to the given partner_id.
    - If REQUIRE_API_KEY: must have valid X-API-Key for this partner
    - Else: partner_id in URL is sufficient (for web UI)
    """
    if not settings.require_api_key:
        return partner_id
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Set X-API-Key header.",
        )
    resolved = await verify_api_key(x_api_key)
    if not resolved:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if resolved != partner_id:
        raise HTTPException(status_code=403, detail="API key does not match partner")
    return partner_id


