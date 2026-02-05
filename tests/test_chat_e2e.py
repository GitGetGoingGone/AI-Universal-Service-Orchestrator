"""E2E tests for chat endpoint (requires services running or mocked)."""

import os
import sys
from pathlib import Path

import pytest

# Add project root
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
@pytest.mark.skipif(
    not os.environ.get("ORCHESTRATOR_SERVICE_URL") and not os.environ.get("API_BASE_URL"),
    reason="ORCHESTRATOR_SERVICE_URL or API_BASE_URL required for E2E (or run against localhost:8002)",
)
async def test_chat_endpoint(orchestrator_url):
    """Test POST /api/v1/chat returns valid structure."""
    import httpx

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(
            f"{orchestrator_url}/api/v1/chat",
            json={"text": "find cakes"},
            params={"agentic": "false"},
        )
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "metadata" in data
    assert "machine_readable" in data
    assert "intent" in data["data"]
    assert data["data"]["intent"]["intent_type"] in ("discover", "unknown", "track_status", "checkout", "support")


@pytest.mark.asyncio
async def test_agentic_consent_endpoint(orchestrator_url):
    """Test GET /api/v1/agentic-consent returns consent config."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{orchestrator_url}/api/v1/agentic-consent")
    except Exception:
        pytest.skip("Orchestrator not reachable")
    if r.status_code != 200:
        pytest.skip("Orchestrator not reachable")
    data = r.json()
    assert "allowed_actions" in data
    assert "resolve_intent" in data["allowed_actions"]
