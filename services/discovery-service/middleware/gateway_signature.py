"""Middleware: require X-Gateway-Signature on /api/* when GATEWAY_SIGNATURE_REQUIRED is true."""

import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from packages.shared.gateway_signature import verify_request

logger = logging.getLogger(__name__)

# Paths that never require Gateway signature (public)
_PUBLIC_PREFIXES = ("/health", "/ready", "/.well-known/", "/openapi.json", "/docs", "/redoc")


async def gateway_signature_middleware(request: Request, call_next: Callable) -> Response:
    """Reject /api/* requests without valid X-Gateway-Signature when gateway_signature_required is True."""
    from config import settings
    if not getattr(settings, "gateway_signature_required", False) or not getattr(settings, "gateway_internal_secret", ""):
        return await call_next(request)

    path = request.scope.get("path", "")
    if not path.startswith("/api/"):
        return await call_next(request)
    for prefix in _PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return await call_next(request)

    signature = request.headers.get("X-Gateway-Signature", "").strip()
    ts_header = request.headers.get("X-Gateway-Timestamp", "").strip()
    try:
        timestamp = int(ts_header) if ts_header else None
    except ValueError:
        timestamp = None

    if not signature or timestamp is None:
        return JSONResponse(
            status_code=401,
            content={"detail": "X-Gateway-Signature and X-Gateway-Timestamp required"},
            headers={"WWW-Authenticate": "GatewaySignature"},
        )

    method = request.scope.get("method", "GET")
    # Verify without body to avoid consuming the stream
    ok = verify_request(
        method,
        path,
        b"",
        signature,
        settings.gateway_internal_secret,
        timestamp=timestamp,
    )
    if not ok:
        logger.warning("Gateway signature verification failed for %s %s", method, path)
        return JSONResponse(
            status_code=403,
            content={"detail": "Invalid or expired X-Gateway-Signature"},
        )
    return await call_next(request)
