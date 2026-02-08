"""Omnichannel Broker Service (Module 24) - Partner communication via API."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
_svc = Path(__file__).resolve().parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_svc))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.partner_webhook import router as webhook_router

app = FastAPI(
    title="Omnichannel Broker Service",
    description="Module 24: Partner communication - change requests via API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)


@app.get("/")
async def root():
    return {
        "service": "omnichannel-broker-service",
        "module": "Omnichannel Message Broker",
        "version": "0.1.0",
        "endpoints": {
            "partner_response": "POST /webhooks/partner - Partner accept/reject",
            "create_change_request": "POST /api/v1/change-request - Create and send change request",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
