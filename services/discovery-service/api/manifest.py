"""AI-First Discoverability (Module 3): Platform manifest for AI agents."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config import settings
from db import get_agent_action_models, get_platform_manifest_config

router = APIRouter(prefix="/api/v1", tags=["Manifest"])


def _build_action_model(action: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    """Format one action model for manifest."""
    endpoint = action.get("endpoint", "")
    if endpoint.startswith("/"):
        full_url = f"{base_url.rstrip('/')}{endpoint}"
    else:
        full_url = f"{base_url.rstrip('/')}/{endpoint}"
    am = {
        "action": action.get("action_name", ""),
        "method": action.get("method", "GET"),
        "endpoint": full_url,
        "requires_auth": bool(action.get("requires_auth", True)),
    }
    if action.get("requires_approval_if_over") is not None:
        am["requires_approval_if_over"] = float(action["requires_approval_if_over"])
    if action.get("rate_limit_per_hour"):
        am["rate_limit"] = f"{action['rate_limit_per_hour']}/hour"
    if action.get("allowed_parameters"):
        am["parameters"] = action["allowed_parameters"]
    if action.get("allowed_modifications"):
        am["allowed_modifications"] = action["allowed_modifications"]
    if action.get("restricted_modifications"):
        am["restricted_modifications"] = action["restricted_modifications"]
    return am


async def _build_manifest() -> Dict[str, Any]:
    """Build full manifest from DB or defaults."""
    base_url = settings.platform_public_url or settings.discovery_public_url or "https://api.usoorchestrator.com"
    base_url = base_url.rstrip("/")

    config = await get_platform_manifest_config()
    actions = await get_agent_action_models()

    if config:
        discovery_endpoint = config.get("discovery_endpoint") or "/api/v1/chat"
        if not discovery_endpoint.startswith("http"):
            discovery_endpoint = f"{base_url}{discovery_endpoint}" if discovery_endpoint.startswith("/") else f"{base_url}/{discovery_endpoint}"
        caps = config.get("capabilities") or {}
        offline = config.get("offline_discovery") or {}
        webhooks = config.get("webhook_endpoints") or {}
        product_schema = config.get("product_schema") or {}
        supported_regions = config.get("supported_regions") or ["US", "CA"]
        max_order_value = float(config.get("max_order_value", 10000))
        currency = config.get("currency") or "USD"
    else:
        discovery_endpoint = f"{base_url}/api/v1/chat"
        caps = {
            "can_initiate_checkout": True,
            "can_modify_order": False,
            "can_cancel_order": True,
            "requires_human_approval_over": 200.00,
            "currency": "USD",
            "supported_regions": ["US", "CA"],
            "max_order_value": 10000.00,
        }
        offline = {"enabled": True, "cache_ttl": 3600, "update_frequency": "hourly"}
        webhooks = {}
        product_schema = {"required_fields": ["product_id", "name", "capabilities", "pricing"]}
        supported_regions = ["US", "CA"]
        max_order_value = 10000.00
        currency = "USD"

    caps.setdefault("currency", currency)
    caps.setdefault("supported_regions", supported_regions)
    caps.setdefault("max_order_value", max_order_value)

    # Static manifest URL for offline discovery (CDN or discovery service)
    discovery_base = settings.discovery_public_url or base_url
    static_url = f"{discovery_base.rstrip('/')}/.well-known/agent-manifest"
    offline.setdefault("static_manifest_url", static_url)

    action_models: List[Dict[str, Any]] = []
    if actions:
        for a in actions:
            action_models.append(_build_action_model(a, base_url))
    else:
        # Fallback defaults
        action_models = [
            _build_action_model(
                {"action_name": "discover_products", "method": "POST", "endpoint": "/api/v1/chat", "requires_auth": False, "rate_limit_per_hour": 100, "allowed_parameters": {"text": "string", "limit": "integer"}},
                base_url,
            ),
            _build_action_model(
                {"action_name": "create_order", "method": "POST", "endpoint": "/api/v1/orders", "requires_auth": True, "requires_approval_if_over": 200, "rate_limit_per_hour": 50, "allowed_parameters": {"bundle_id": "uuid", "delivery_address": "object"}},
                base_url,
            ),
            _build_action_model(
                {"action_name": "modify_order", "method": "PATCH", "endpoint": "/api/v1/orders/{id}", "requires_auth": True, "rate_limit_per_hour": 30},
                base_url,
            ),
            _build_action_model(
                {"action_name": "cancel_order", "method": "DELETE", "endpoint": "/api/v1/orders/{id}", "requires_auth": True, "rate_limit_per_hour": 20},
                base_url,
            ),
            _build_action_model(
                {"action_name": "track_order", "method": "GET", "endpoint": "/api/v1/orders/{id}/status", "requires_auth": True, "rate_limit_per_hour": 60},
                base_url,
            ),
        ]

    manifest = {
        "manifest_version": config.get("manifest_version", "1.0") if config else "1.0",
        "platform_id": config.get("platform_id", "uso-orchestrator") if config else "uso-orchestrator",
        "platform_name": config.get("platform_name", "AI Universal Service Orchestrator") if config else "AI Universal Service Orchestrator",
        "discovery_endpoint": discovery_endpoint,
        "capabilities": caps,
        "action_models": action_models,
        "product_schema": product_schema,
        "offline_discovery": offline,
        "webhook_endpoints": webhooks,
    }
    return manifest


@router.get("/manifest")
async def get_manifest():
    """
    ACP-style platform manifest for AI agents.
    Includes action models, capabilities, offline discovery config.
    Cache TTL suggested in offline_discovery.cache_ttl.
    """
    manifest = await _build_manifest()
    return JSONResponse(
        content=manifest,
        headers={
            "Cache-Control": f"public, max-age={manifest.get('offline_discovery', {}).get('cache_ttl', 3600)}",
        },
    )
