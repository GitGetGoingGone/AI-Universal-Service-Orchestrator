"""Webhook Push Notification Bridge - push updates to ChatGPT, Gemini, WhatsApp."""

import sys
from pathlib import Path

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

from config import settings
from db import check_connection
from api.push import router as push_router

app = FastAPI(
    title="Webhook Push Notification Bridge",
    description="Push updates to ChatGPT, Gemini, WhatsApp chat threads",
    version="0.1.0",
)

app.middleware("http")(request_id_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(USOException, uso_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(push_router)

health_checker = HealthChecker("webhook-service", "0.1.0")


async def check_database() -> DependencyCheck:
    """Check database connectivity."""
    if not settings.supabase_configured:
        return DependencyCheck(
            name="database",
            status=DependencyStatus.UNHEALTHY,
            message="Supabase not configured",
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


health_checker.add_check("database", check_database)
app.include_router(health_router(health_checker))


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "webhook-service",
        "description": "Webhook Push Notification Bridge",
        "version": "0.1.0",
        "endpoints": {
            "push": "POST /api/v1/webhooks/chat/{platform}/{thread_id}",
            "push_alt": "POST /api/v1/webhooks/push",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }
