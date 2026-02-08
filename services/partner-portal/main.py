"""Partner Portal (Module 9) - Production-grade partner onboarding and management."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
_svc = Path(__file__).resolve().parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_svc))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.partners import router as partners_router
from api.products import router as products_router
from api.admins import router as admins_router
from api.analytics import router as analytics_router
from api.availability_integrations import router as availability_integrations_router
from api.earnings import router as earnings_router
from api.inventory import router as inventory_router
from api.notifications import router as notifications_router
from api.operations import router as operations_router
from api.promotions import router as promotions_router
from api.ratings import router as ratings_router
from api.orders import router as orders_router
from api.schedule import router as schedule_router
from api.team import router as team_router
from config import settings

# Shared packages
from packages.shared.errors.middleware import (
    generic_exception_handler,
    request_id_middleware,
    uso_exception_handler,
)
from packages.shared.errors.exceptions import USOException
from packages.shared.monitoring.logging import configure_logging, get_logger
from packages.shared.monitoring.health import (
    DependencyCheck,
    DependencyStatus,
    HealthChecker,
    health_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifespan."""
    configure_logging(
        service_name="partner-portal",
        level=settings.log_level,
        json_format=settings.is_production,
    )
    yield


app = FastAPI(
    title="Partner Portal",
    description="Production-grade partner onboarding, product registration, and channel configuration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID
app.middleware("http")(request_id_middleware)


# Auth: extract user from Bearer token or X-API-Key, set request.state.user
@app.middleware("http")
async def auth_middleware(request, call_next):
    """Extract user from Authorization or X-API-Key and set request.state.user."""
    request.state.user = None
    auth_header = request.headers.get("Authorization")
    api_key = request.headers.get("X-API-Key")

    if api_key:
        from db import verify_api_key
        partner_id = await verify_api_key(api_key)
        if partner_id:
            request.state.user = {"id": f"api:{partner_id}", "partner_id": partner_id}

    elif auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            from auth import _verify_clerk_token
            payload = await _verify_clerk_token(token)
            if payload:
                request.state.user = {
                    "id": payload.get("sub"),
                    "email": payload.get("email"),
                }

    response = await call_next(request)
    return response


# Exception handlers
app.add_exception_handler(USOException, uso_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Health
health_checker = HealthChecker(service_name="partner-portal", version="1.0.0")


async def db_health_check() -> DependencyCheck:
    """Check Supabase connectivity."""
    from db import get_supabase

    client = get_supabase()
    if not client:
        return DependencyCheck(
            name="supabase",
            status=DependencyStatus.UNHEALTHY,
            message="Supabase not configured",
        )
    try:
        client.table("partners").select("id").limit(1).execute()
        return DependencyCheck(name="supabase", status=DependencyStatus.HEALTHY)
    except Exception as e:
        return DependencyCheck(
            name="supabase",
            status=DependencyStatus.UNHEALTHY,
            message=str(e),
        )


health_checker.add_check("supabase", db_health_check)
app.include_router(health_router(health_checker))


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    """Add security headers."""
    response = await call_next(request)
    if settings.secure_headers:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

app.include_router(partners_router)
app.include_router(products_router)
app.include_router(admins_router)
app.include_router(analytics_router)
app.include_router(availability_integrations_router)
app.include_router(earnings_router)
app.include_router(inventory_router)
app.include_router(notifications_router)
app.include_router(operations_router)
app.include_router(promotions_router)
app.include_router(ratings_router)
app.include_router(orders_router)
app.include_router(schedule_router)
app.include_router(team_router)


@app.post("/webhooks/partner/{partner_id}/availability")
async def webhook_availability(partner_id: str, payload: dict):
    """Webhook for partner to push availability. Verify signature in production."""
    # TODO: verify X-Webhook-Signature or similar
    return {"received": True, "message": "Webhook endpoint - implement merge logic"}


@app.get("/")
async def root():
    """Portal info and links."""
    return {
        "service": "partner-portal",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "onboard": "GET /api/v1/onboard",
            "partners": "GET /api/v1/partners",
            "products": "GET /api/v1/partners/{id}/products",
            "settings": "GET /api/v1/partners/{id}/settings",
            "demo_chat": "GET /api/v1/partners/{id}/demo-chat",
            "respond": "POST /api/v1/partners/{id}/respond",
        },
    }


@app.get("/docs/openapi-partner-actions.yaml", include_in_schema=False)
async def openapi_partner_actions():
    """OpenAPI spec for ChatGPT/Gemini partner actions."""
    path = _root / "docs" / "openapi-partner-actions.yaml"
    if path.exists():
        return FileResponse(path, media_type="application/yaml")
    return {"error": "OpenAPI spec not found"}
