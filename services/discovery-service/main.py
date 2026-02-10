"""Discovery Service (Module 1) - FastAPI app with shared error handling."""

import sys
from pathlib import Path

# Add shared package and parent to path
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from api.admin import router as admin_router
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
app.include_router(admin_router)
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
            "inventory_webhook": "POST /webhooks/inventory",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }
