"""Hybrid Response Service (Module 13) - AI vs Human routing."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import check_connection
from api.classify import router as classify_router

app = FastAPI(
    title="Hybrid Response Service",
    description="Module 13: Classify and route to AI or human",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(classify_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hybrid-response-service"}


@app.get("/ready")
def ready():
    ok = check_connection()
    return {"ready": ok, "database": "connected" if ok else "disconnected"}
