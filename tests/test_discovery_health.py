"""Server-based tests for discovery service health endpoints."""

import pytest
import httpx


@pytest.mark.server
def test_health_liveness(discovery_base_url: str) -> None:
    """GET /health returns 200 and healthy status."""
    r = httpx.get(f"{discovery_base_url}/health", timeout=10.0)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "healthy"
    assert "service" in data
    assert "version" in data


@pytest.mark.server
def test_health_readiness(discovery_base_url: str) -> None:
    """GET /ready returns 200 and includes dependency checks."""
    r = httpx.get(f"{discovery_base_url}/ready", timeout=10.0)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") in ("healthy", "unhealthy", "degraded")
    assert "service" in data
    assert "dependencies" in data
    assert isinstance(data["dependencies"], list)


@pytest.mark.server
def test_root_service_info(discovery_base_url: str) -> None:
    """GET / returns service metadata and endpoints."""
    r = httpx.get(discovery_base_url, timeout=10.0)
    assert r.status_code == 200
    data = r.json()
    assert data.get("service") == "discovery-service"
    assert "module" in data
    assert "version" in data
    assert "endpoints" in data
    assert "discover" in data.get("endpoints", {})
