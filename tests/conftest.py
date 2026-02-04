"""Pytest configuration for server-based tests."""

import os

import pytest


def _get_base_url() -> str:
    """Resolve discovery service base URL from environment."""
    url = os.environ.get("DISCOVERY_SERVICE_URL") or os.environ.get("API_BASE_URL")
    if not url:
        pytest.skip(
            "DISCOVERY_SERVICE_URL or API_BASE_URL must be set for server tests. "
            "Example: export DISCOVERY_SERVICE_URL=http://localhost:8000"
        )
    return url.rstrip("/")


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for discovery service (from env)."""
    return _get_base_url()


@pytest.fixture(scope="session")
def discovery_base_url(base_url: str) -> str:
    """Alias for discovery service base URL."""
    return base_url
