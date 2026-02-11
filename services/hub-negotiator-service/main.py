"""HubNegotiator Service (Module 10) - RFP & Bidding."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import check_connection
from api.rfp import router as rfp_router

app = FastAPI(
    title="HubNegotiator Service",
    description="Module 10: RFP & Bidding",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rfp_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hub-negotiator-service"}


@app.get("/ready")
async def ready():
    ok = await check_connection()
    return {"ready": ok, "database": "connected" if ok else "disconnected"}
