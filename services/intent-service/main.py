"""Intent Service (Module 4) - FastAPI app with shared error handling."""

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
from api.resolve import router as resolve_router

app = FastAPI(
    title="Intent Service",
    description="Module 4: Intent Resolver - Natural language to structured intent",
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

app.include_router(resolve_router)

health_checker = HealthChecker("intent-service", "0.1.0")


async def check_database() -> DependencyCheck:
    """Check database connectivity."""
    if not settings.supabase_configured:
        return DependencyCheck(
            name="database",
            status=DependencyStatus.UNHEALTHY,
            message="Supabase not configured",
        )
    try:
        ok = check_connection()
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


async def check_llm() -> DependencyCheck:
    """Check Azure OpenAI availability (optional)."""
    if settings.azure_openai_configured:
        return DependencyCheck(
            name="azure_openai",
            status=DependencyStatus.HEALTHY,
            message="Configured",
        )
    return DependencyCheck(
        name="azure_openai",
        status=DependencyStatus.DEGRADED,
        message="Not configured; using fallback heuristics",
    )


health_checker.add_check("database", check_database)
health_checker.add_check("llm", check_llm)
app.include_router(health_router(health_checker))


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "intent-service",
        "module": "Intent Resolver",
        "version": "0.1.0",
        "endpoints": {
            "resolve": "POST /api/v1/resolve",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }
