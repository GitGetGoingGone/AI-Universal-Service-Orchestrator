"""Re-Sourcing Service (Module 6) - Autonomous recovery when partners reject."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
_svc = Path(__file__).resolve().parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_svc))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.recovery import router as recovery_router

app = FastAPI(
    title="Re-Sourcing Service",
    description="Module 6: Autonomous Re-Sourcing - find alternatives when partners reject",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recovery_router)


@app.get("/")
async def root():
    return {
        "service": "re-sourcing-service",
        "module": "Autonomous Re-Sourcing",
        "version": "0.1.0",
        "endpoints": {
            "trigger": "POST /api/v1/recovery/trigger - Handle partner rejection",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
