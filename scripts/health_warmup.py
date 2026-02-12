#!/usr/bin/env python3
"""Health check and warmup for all services. Run before E2E tests."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root))


SERVICES = [
    ("discovery", os.getenv("DISCOVERY_SERVICE_URL", "http://localhost:8000"), "/health"),
    ("orchestrator", os.getenv("ORCHESTRATOR_SERVICE_URL", "http://localhost:8002"), "/health"),
    ("intent", os.getenv("INTENT_SERVICE_URL", "http://localhost:8001"), "/health"),
    ("webhook", os.getenv("WEBHOOK_SERVICE_URL", "http://localhost:8003"), "/health"),
    ("proofing", os.getenv("PROOFING_SERVICE_URL", "http://localhost:8007"), "/health"),
]


async def check_one(name: str, base: str, path: str) -> bool:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base.rstrip('/')}{path}")
            ok = r.status_code == 200
            print(f"  {name}: {'OK' if ok else 'FAIL'}")
            return ok
    except Exception as e:
        print(f"  {name}: FAIL ({e})")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Health check all services")
    parser.add_argument("--fail-fast", action="store_true", help="Exit on first failure")
    args = parser.parse_args()
    all_ok = True
    for name, base, path in SERVICES:
        ok = await check_one(name, base, path)
        if not ok and args.fail_fast:
            sys.exit(1)
        all_ok = all_ok and ok
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
