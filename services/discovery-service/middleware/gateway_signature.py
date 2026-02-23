"""Middleware: require X-Gateway-Signature on /api/* when GATEWAY_SIGNATURE_REQUIRED is true; always require for /api/v1/ucp/*."""

import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.requests import Request as StarletteRequest

from packages.shared.gateway_signature import verify_request, verify_request_no_body

logger = logging.getLogger(__name__)

# Paths that never require Gateway signature (public)
_PUBLIC_PREFIXES = ("/health", "/ready", "/.well-known/", "/openapi.json", "/docs", "/redoc")

# UCP path prefix: always require signature when secret is configured
_UCP_PATH_PREFIX = "/api/v1/ucp/"


async def gateway_signature_middleware(request: Request, call_next: Callable) -> Response:
    """Require X-Gateway-Signature for /api/v1/ucp/* (always when secret set). For other /api/*, require when gateway_signature_required is True."""
    from config import settings
    path = request.scope.get("path", "")
    method = request.scope.get("method", "GET")

    for prefix in _PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return await call_next(request)

    # UCP: always require signature when GATEWAY_INTERNAL_SECRET is set
    secret = getattr(settings, "gateway_internal_secret", "") or ""
    if path.startswith(_UCP_PATH_PREFIX):
        if not secret:
            return JSONResponse(
                status_code=503,
                content={"detail": "UCP requires Gateway signature but GATEWAY_INTERNAL_SECRET is not set"},
                headers={"WWW-Authenticate": "GatewaySignature"},
            )
        signature = request.headers.get("X-Gateway-Signature", "").strip()
        ts_header = request.headers.get("X-Gateway-Timestamp", "").strip()
        try:
            timestamp = int(ts_header) if ts_header else None
        except ValueError:
            timestamp = None
        if not signature or timestamp is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "X-Gateway-Signature and X-Gateway-Timestamp required for UCP"},
                headers={"WWW-Authenticate": "GatewaySignature"},
            )
        if method in ("POST", "PUT", "PATCH"):
            body = await request.body()
            ok = verify_request(method, path, body, signature, secret, timestamp=timestamp)
            # Re-set body for downstream (Starlette consumes body once)
            async def receive():
                return {"type": "http.request", "body": body}
            request = StarletteRequest(request.scope, receive)
        else:
            ok = verify_request_no_body(method, path, signature, secret, timestamp=timestamp)
        if not ok:
            logger.warning("Gateway signature verification failed for UCP %s %s", method, path)
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid or expired X-Gateway-Signature"},
            )
        return await call_next(request)

    # Non-UCP /api/*: require signature only when gateway_signature_required is True
    if not getattr(settings, "gateway_signature_required", False) or not secret:
        return await call_next(request)
    if not path.startswith("/api/"):
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

    # Verify without body to avoid consuming the stream (legacy behavior for non-UCP)
    ok = verify_request(
        method,
        path,
        b"",
        signature,
        secret,
        timestamp=timestamp,
    )
    if not ok:
        logger.warning("Gateway signature verification failed for %s %s", method, path)
        return JSONResponse(
            status_code=403,
            content={"detail": "Invalid or expired X-Gateway-Signature"},
        )
    return await call_next(request)
