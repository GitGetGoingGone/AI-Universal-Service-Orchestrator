"""Google id_token verification for Link Account (no mocks)."""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def verify_google_id_token(id_token: str, client_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Verify Google OAuth2 id_token and return payload (sub, email, name).
    Returns None if verification fails or client_id not configured.
    """
    if not client_id:
        return None
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        payload = id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            client_id,
        )
        if not payload or not payload.get("sub"):
            return None
        return {
            "sub": payload["sub"],
            "email": payload.get("email"),
            "name": payload.get("name"),
            "email_verified": payload.get("email_verified"),
        }
    except Exception as e:
        logger.warning("Google id_token verification failed: %s", e)
        return None
