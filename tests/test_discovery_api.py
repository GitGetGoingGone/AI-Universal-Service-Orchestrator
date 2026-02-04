"""Server-based tests for discovery service API contract."""

import pytest
import httpx


@pytest.mark.server
def test_discover_returns_200_with_valid_structure(discovery_base_url: str) -> None:
    """GET /api/v1/discover returns 200 and Chat-First response structure."""
    r = httpx.get(
        f"{discovery_base_url}/api/v1/discover",
        params={"intent": "flowers"},
        timeout=10.0,
    )
    assert r.status_code == 200
    data = r.json()

    # Required top-level keys per OpenAPI
    assert "data" in data
    assert "machine_readable" in data
    assert "adaptive_card" in data
    assert "metadata" in data

    # data shape
    assert "products" in data["data"]
    assert "count" in data["data"]
    assert isinstance(data["data"]["products"], list)
    assert data["data"]["count"] == len(data["data"]["products"])

    # JSON-LD (schema.org ItemList)
    mr = data["machine_readable"]
    assert mr.get("@context") == "https://schema.org"
    assert mr.get("@type") == "ItemList"
    assert "numberOfItems" in mr
    assert "itemListElement" in mr

    # Adaptive Card
    ac = data["adaptive_card"]
    assert ac.get("type") == "AdaptiveCard"
    assert "body" in ac

    # metadata
    assert "api_version" in data["metadata"]
    assert "timestamp" in data["metadata"]
    assert "request_id" in data["metadata"]


@pytest.mark.server
def test_discover_requires_intent(discovery_base_url: str) -> None:
    """GET /api/v1/discover without intent returns 422."""
    r = httpx.get(f"{discovery_base_url}/api/v1/discover", timeout=10.0)
    assert r.status_code == 422


@pytest.mark.server
def test_discover_respects_limit(discovery_base_url: str) -> None:
    """GET /api/v1/discover with limit returns at most that many products."""
    r = httpx.get(
        f"{discovery_base_url}/api/v1/discover",
        params={"intent": "flowers", "limit": 3},
        timeout=10.0,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["data"]["count"] <= 3
    assert len(data["data"]["products"]) <= 3


@pytest.mark.server
def test_discover_accepts_optional_params(discovery_base_url: str) -> None:
    """GET /api/v1/discover accepts location and partner_id without error."""
    r = httpx.get(
        f"{discovery_base_url}/api/v1/discover",
        params={
            "intent": "chocolates",
            "location": "NYC",
            "partner_id": "00000000-0000-0000-0000-000000000000",
        },
        timeout=10.0,
    )
    # Should not 500; may return 200 with empty/filtered results
    assert r.status_code in (200, 422)
