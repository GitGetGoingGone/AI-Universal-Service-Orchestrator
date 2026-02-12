"""E2E tests: Standing Intent API (Intent → Discovery → Standing Intent)."""

import os
import sys
from pathlib import Path

import pytest

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root))


def _get_orchestrator_url() -> str:
    url = os.environ.get("ORCHESTRATOR_SERVICE_URL") or os.environ.get("API_BASE_URL")
    if url:
        return url.rstrip("/")
    return "http://localhost:8002"


@pytest.fixture(scope="module")
def orchestrator_url():
    return _get_orchestrator_url()


@pytest.mark.asyncio
async def test_standing_intents_list(orchestrator_url):
    """Test GET /api/v1/standing-intents returns list."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{orchestrator_url}/api/v1/standing-intents")
    except Exception:
        pytest.skip("Orchestrator not reachable")
    assert r.status_code == 200
    data = r.json()
    assert "standing_intents" in data
    assert "count" in data
    assert isinstance(data["standing_intents"], list)


@pytest.mark.asyncio
async def test_standing_intent_create(orchestrator_url):
    """Test POST /api/v1/standing-intents creates intent (requires Durable Orchestrator)."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{orchestrator_url}/api/v1/standing-intents",
                json={
                    "intent_description": "Notify me when floral arrangements are in stock",
                    "approval_timeout_hours": 24,
                },
            )
    except Exception:
        pytest.skip("Orchestrator not reachable")
    if r.status_code == 503:
        pytest.skip("Durable Orchestrator unavailable or kill switch active")
    assert r.status_code in (200, 201)
    data = r.json()
    assert "orchestration_instance_id" in data or "status" in data


@pytest.mark.asyncio
async def test_kill_switch_status(orchestrator_url):
    """Test GET /api/v1/admin/kill-switch returns status."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{orchestrator_url}/api/v1/admin/kill-switch")
    except Exception:
        pytest.skip("Orchestrator not reachable")
    assert r.status_code == 200
    data = r.json()
    assert "kill_switch_active" in data
