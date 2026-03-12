#!/usr/bin/env python3
"""
SLA Re-Sourcing Job: find legs where partner hasn't started design within SLA,
notify user, store alternatives. Run via cron (e.g. every 15 min).
Usage: DISCOVERY_SERVICE_URL=... WEBHOOK_SERVICE_URL=... python scripts/sla_re_sourcing_job.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root))

import httpx


async def run():
    discovery_url = os.getenv("DISCOVERY_SERVICE_URL", "http://localhost:8000").rstrip("/")
    webhook_url = os.getenv("WEBHOOK_SERVICE_URL", "http://localhost:8003").rstrip("/")

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{discovery_url}/api/v1/sla/run-job")
        if r.status_code != 200:
            print(f"SLA job failed: {r.status_code} {r.text}")
            sys.exit(1)
        data = r.json()
        notified = data.get("notified", [])
        for n in notified:
            thread_id = n.get("thread_id")
            leg_id = n.get("leg_id")
            alt = n.get("alternatives", [])
            if thread_id and alt:
                msg = {
                    "narrative": f"Your partner hasn't started your design yet. We found similar options. Would you like to switch?",
                    "adaptive_card": {
                        "type": "AdaptiveCard",
                        "body": [
                            {"type": "TextBlock", "text": "Your partner hasn't started your design yet.", "wrap": True},
                            {"type": "TextBlock", "text": f"We found {len(alt)} similar option(s). Would you like to switch?", "wrap": True},
                        ],
                        "actions": [
                            {"type": "Action.Submit", "title": "Yes, switch", "data": {"action": "sla_switch_confirm", "leg_id": leg_id}},
                            {"type": "Action.Submit", "title": "No, keep waiting", "data": {"action": "sla_switch_decline"}},
                        ],
                    },
                }
                try:
                    await client.post(
                        f"{webhook_url}/api/v1/webhooks/chat/web/{thread_id}",
                        json=msg,
                    )
                except Exception as e:
                    print(f"Webhook push failed for {thread_id}: {e}")
        print(f"SLA job done: {len(notified)} notified")


if __name__ == "__main__":
    asyncio.run(run())
