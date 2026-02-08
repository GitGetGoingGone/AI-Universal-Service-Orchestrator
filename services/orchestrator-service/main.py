"""Orchestrator Service - Intent → Discovery flow."""

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
from packages.shared.monitoring import HealthChecker, health_router
from packages.shared.monitoring.health import DependencyCheck, DependencyStatus

from config import settings
from api.chat import router as chat_router
from api.products import router as products_router

app = FastAPI(
    title="Orchestrator Service",
    description="Intent → Discovery orchestration. Chat-First single endpoint.",
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

app.include_router(chat_router)
app.include_router(products_router)

health_checker = HealthChecker("orchestrator-service", "0.1.0")


async def check_intent_service() -> DependencyCheck:
    """Check Intent service reachability."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.intent_service_url}/health")
            ok = r.status_code == 200
    except Exception as e:
        return DependencyCheck(
            name="intent_service",
            status=DependencyStatus.UNHEALTHY,
            message=str(e),
        )
    return DependencyCheck(
        name="intent_service",
        status=DependencyStatus.HEALTHY if ok else DependencyStatus.UNHEALTHY,
        message="Connected" if ok else "Unreachable",
    )


async def check_discovery_service() -> DependencyCheck:
    """Check Discovery service reachability."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.discovery_service_url}/health")
            ok = r.status_code == 200
    except Exception as e:
        return DependencyCheck(
            name="discovery_service",
            status=DependencyStatus.UNHEALTHY,
            message=str(e),
        )
    return DependencyCheck(
        name="discovery_service",
        status=DependencyStatus.HEALTHY if ok else DependencyStatus.UNHEALTHY,
        message="Connected" if ok else "Unreachable",
    )


health_checker.add_check("intent_service", check_intent_service)
health_checker.add_check("discovery_service", check_discovery_service)
app.include_router(health_router(health_checker))


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "orchestrator-service",
        "description": "Agentic AI + AI Agents Chat Entry Point",
        "version": "0.2.0",
        "endpoints": {
            "chat": "POST /api/v1/chat",
            "products": "GET /api/v1/products/{id}",
            "bundles": "GET /api/v1/bundles/{id}",
            "bundle_add": "POST /api/v1/bundle/add",
            "bundle_remove": "POST /api/v1/bundle/remove",
            "checkout": "POST /api/v1/checkout",
            "agentic_consent": "GET /api/v1/agentic-consent",
            "agentic_handoff": "GET /api/v1/agentic-handoff",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }
