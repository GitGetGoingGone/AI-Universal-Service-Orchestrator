"""Gateway UCP: single /.well-known/ucp for USO and proxy routes to Discovery."""

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from config import settings

router = APIRouter(tags=["Gateway UCP"])


@router.get("/.well-known/ucp")
async def well_known_ucp():
    """
    Single USO UCP manifest. All endpoints point to the Gateway (orchestrator).
    External clients discover and call only the Gateway; no internal agent URLs.
    """
    base = settings.gateway_public_url or settings.orchestrator_base_url
    base = base.rstrip("/")
    body = {
        "ucp": {
            "version": "2026-01-11",
            "services": {
                "dev.ucp.shopping": {
                    "version": "2026-01-11",
                    "spec": "https://ucp.dev/specification/overview",
                    "rest": {
                        "schema": f"{base}/api/v1/gateway/ucp/rest.openapi.json",
                        "endpoint": f"{base}/api/v1/gateway/ucp",
                    },
                },
            },
            "capabilities": [
                {
                    "name": "dev.ucp.shopping.checkout",
                    "version": "2026-01-11",
                    "spec": "https://ucp.dev/specification/checkout",
                    "schema": "https://ucp.dev/schemas/shopping/checkout.json",
                },
            ],
        },
    }
    return JSONResponse(
        content=body,
        headers={
            "Content-Type": "application/json",
            "Cache-Control": "public, max-age=3600",
        },
    )


def _discovery_url(path: str) -> str:
    """Build Discovery service URL for a path under /api/v1/ucp."""
    base = settings.discovery_service_url.rstrip("/")
    # gateway path /api/v1/gateway/ucp/items -> discovery /api/v1/ucp/items
    if path.startswith("/api/v1/gateway/ucp/"):
        path = "/api/v1/ucp/" + path.split("/api/v1/gateway/ucp/", 1)[-1]
    elif path == "/api/v1/gateway/ucp" or path.rstrip("/") == "/api/v1/gateway/ucp":
        path = "/api/v1/ucp"
    return f"{base}{path}"


@router.get("/api/v1/gateway/ucp/items")
async def gateway_ucp_items(request: Request):
    """Proxy to Discovery UCP catalog (searchGifts)."""
    url = _discovery_url("/api/v1/ucp/items")
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, params=params)
    return Response(
        content=r.content,
        status_code=r.status_code,
        headers={k: v for k, v in r.headers.items() if k.lower() not in ("transfer-encoding", "connection")},
        media_type=r.headers.get("content-type"),
    )


@router.post("/api/v1/gateway/ucp/checkout")
async def gateway_ucp_checkout(request: Request):
    """Proxy to Discovery UCP checkout."""
    url = _discovery_url("/api/v1/ucp/checkout")
    body = await request.body()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, content=body, headers={"Content-Type": request.headers.get("content-type", "application/json")})
    return Response(
        content=r.content,
        status_code=r.status_code,
        headers={k: v for k, v in r.headers.items() if k.lower() not in ("transfer-encoding", "connection")},
        media_type=r.headers.get("content-type"),
    )


@router.get("/api/v1/gateway/ucp/rest.openapi.json")
async def gateway_ucp_rest_openapi(request: Request):
    """Proxy to Discovery UCP OpenAPI schema."""
    url = _discovery_url("/api/v1/ucp/rest.openapi.json")
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url)
    return Response(
        content=r.content,
        status_code=r.status_code,
        headers={k: v for k, v in r.headers.items() if k.lower() not in ("transfer-encoding", "connection")},
        media_type=r.headers.get("content-type"),
    )
