"""Payment Service (Module 15) - Stripe Connect for atomic multi-checkout."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
_svc = Path(__file__).resolve().parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_svc))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.checkout import router as checkout_router
from webhooks.stripe_webhook import router as stripe_webhook_router

app = FastAPI(
    title="Payment Service",
    description="Module 15: Atomic Multi-Checkout with Stripe",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(checkout_router)
app.include_router(stripe_webhook_router)


@app.get("/")
async def root():
    return {
        "service": "payment-service",
        "module": "Atomic Multi-Checkout",
        "version": "0.1.0",
        "endpoints": {
            "create_payment": "POST /api/v1/payment/create - Create PaymentIntent",
            "stripe_webhook": "POST /webhooks/stripe - Stripe webhook",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
