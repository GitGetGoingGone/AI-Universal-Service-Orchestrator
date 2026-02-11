"""Virtual Proofing Engine Service (Module 8) - DALL-E proof preview & approval."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import check_connection
from api.proofs import router as proofs_router

app = FastAPI(
    title="Virtual Proofing Service",
    description="Module 8: DALL-E proof preview, approval workflow",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proofs_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "proofing-service", "dalle_configured": settings.dalle_configured}


@app.get("/ready")
async def ready():
    ok = await check_connection()
    return {"ready": ok, "database": "connected" if ok else "disconnected"}
