"""Partner Portal (Module 9) - FastAPI app for partner onboarding and product registration."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
_svc = Path(__file__).resolve().parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_svc))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.partners import router as partners_router
from api.products import router as products_router

app = FastAPI(
    title="Partner Portal",
    description="Module 9: Generic Capability Portal - Partner onboarding, product registration, webhook config",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))

app.include_router(partners_router)
app.include_router(products_router)


@app.get("/")
async def root():
    """Portal info and links."""
    return {
        "service": "partner-portal",
        "module": "Generic Capability Portal",
        "version": "0.1.0",
        "endpoints": {
            "onboard": "GET /api/v1/onboard - Partner onboarding form",
            "partners": "GET /api/v1/partners - List partners",
            "products": "GET /api/v1/partners/{id}/products - Product registration",
            "settings": "GET /api/v1/partners/{id}/settings - Webhook config",
        },
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}
