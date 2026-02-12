"""Discovery Service (Module 1) - FastAPI app with shared error handling."""

import sys
from pathlib import Path

# Add shared package and parent to path
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from packages.shared.errors import USOException
from packages.shared.errors.middleware import (
    request_id_middleware,
    uso_exception_handler,
    generic_exception_handler,
)
from packages.shared.monitoring import HealthChecker, DependencyStatus, health_router
from packages.shared.monitoring.health import DependencyCheck

# Import after path setup - discovery-service modules
from config import settings
from db import check_connection
from api.products import router as products_router
from api.partners import router as partners_router
from api.admin import router as admin_router
from api.ucp import router as ucp_router
from api.ucp_checkout import router as ucp_checkout_router
from api.feeds import router as feeds_router
from api.manifest import router as manifest_router, _build_manifest
from api.orders import router as orders_router
from webhooks.inventory_webhook import router as webhooks_router

app = FastAPI(
    title="Discovery Service",
    description="Module 1: Multi-Protocol Scout Engine",
    version="0.1.0",
)

# Middleware
app.middleware("http")(request_id_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(USOException, uso_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# API routes
app.include_router(products_router)
app.include_router(partners_router)
app.include_router(admin_router)
app.include_router(ucp_router)
app.include_router(ucp_checkout_router)
app.include_router(feeds_router)
app.include_router(manifest_router)
app.include_router(orders_router)
app.include_router(webhooks_router)

# Health checks (per 07-project-operations.md)
health_checker = HealthChecker("discovery-service", "0.1.0")


async def check_database() -> DependencyCheck:
    """Check database connectivity."""
    if not settings.supabase_configured:
        return DependencyCheck(
            name="database",
            status=DependencyStatus.UNHEALTHY,
            message="Supabase not configured (SUPABASE_URL, SUPABASE_SECRET_KEY)",
        )
    try:
        ok = await check_connection()
        return DependencyCheck(
            name="database",
            status=DependencyStatus.HEALTHY if ok else DependencyStatus.UNHEALTHY,
            message="Connected" if ok else "Connection failed",
        )
    except Exception as e:
        return DependencyCheck(
            name="database",
            status=DependencyStatus.UNHEALTHY,
            message=str(e),
        )


async def check_cache() -> DependencyCheck:
    """Check cache connectivity. TODO: Add Redis/Upstash when implemented."""
    return DependencyCheck(
        name="cache",
        status=DependencyStatus.HEALTHY,
        message="Not yet configured (optional)",
    )


health_checker.add_check("database", check_database)
health_checker.add_check("cache", check_cache)
app.include_router(health_router(health_checker))


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "discovery-service",
        "module": "Multi-Protocol Scout Engine",
        "version": "0.1.0",
        "endpoints": {
            "discover": "GET /api/v1/discover?intent=<query>",
            "manifest_ingest": "POST /api/v1/admin/manifest/ingest",
            "embedding_backfill": "POST /api/v1/admin/embeddings/backfill",
            "ucp_catalog": "GET /api/v1/ucp/items",
            "well_known_ucp": "GET /.well-known/ucp",
            "acp_feed": "GET /api/v1/feeds/acp?partner_id=<optional>",
            "agent_manifest": "GET /api/v1/manifest | /.well-known/agent-manifest",
            "order_status": "GET /api/v1/orders/{id}/status",
            "push_feed": "POST /api/v1/feeds/push",
            "push_status": "GET /api/v1/feeds/push-status?partner_id=",
            "inventory_webhook": "POST /webhooks/inventory",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }


@app.get("/.well-known/agent-manifest")
async def well_known_agent_manifest():
    """
    AI-First Discoverability (Module 3): Platform manifest for AI agents at well-known URL.
    Same content as GET /api/v1/manifest; discoverable by convention.
    """
    manifest = await _build_manifest()
    return JSONResponse(
        content=manifest,
        headers={
            "Cache-Control": f"public, max-age={manifest.get('offline_discovery', {}).get('cache_ttl', 3600)}",
        },
    )


@app.get("/.well-known/ucp")
async def well_known_ucp():
    """
    UCP Business Profile for Google/Gemini discovery.
    Platform discovers us via this URL and calls our catalog API.
    """
    base = (settings.discovery_public_url or "").rstrip("/")
    if not base:
        base = "https://uso-discovery.onrender.com"
    return {
        "ucp": {
            "version": "2026-01-11",
            "services": {
                "dev.ucp.shopping": {
                    "version": "2026-01-11",
                    "spec": "https://ucp.dev/specification/overview",
                    "rest": {
                        "schema": "https://ucp.dev/services/shopping/rest.openapi.json",
                        "endpoint": f"{base}/api/v1/ucp",
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
