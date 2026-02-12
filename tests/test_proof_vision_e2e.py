"""E2E tests: Proof → Approve → Vision AI."""

import os
import sys
from pathlib import Path

import pytest

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root))


def _get_proofing_url() -> str:
    url = os.environ.get("PROOFING_SERVICE_URL")
    if url:
        return url.rstrip("/")
    return "http://localhost:8007"


@pytest.fixture(scope="module")
def proofing_url():
    return _get_proofing_url()


@pytest.mark.asyncio
async def test_create_proof(proofing_url):
    """Test POST /api/v1/proofs creates proof state."""
    import httpx
    # Need a valid order_id - use a known test order or skip
    skip = not os.environ.get("TEST_ORDER_ID")
    if skip:
        pytest.skip("TEST_ORDER_ID required for proof creation")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{proofing_url}/api/v1/proofs",
                json={"order_id": os.environ["TEST_ORDER_ID"], "proof_type": "virtual_preview"},
            )
    except Exception:
        pytest.skip("Proofing service not reachable")
    assert r.status_code in (200, 201)
    data = r.json()
    assert "id" in data
    assert data.get("current_state") == "pending"


@pytest.mark.asyncio
async def test_list_proofs(proofing_url):
    """Test GET /api/v1/proofs returns list."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{proofing_url}/api/v1/proofs")
    except Exception:
        pytest.skip("Proofing service not reachable")
    assert r.status_code == 200
    data = r.json()
    assert "proofs" in data
    assert "count" in data
