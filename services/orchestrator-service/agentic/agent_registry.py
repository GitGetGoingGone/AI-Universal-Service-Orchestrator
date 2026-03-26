"""Built-in multi-agent registry merged with platform_config.multi_agent_config."""

from __future__ import annotations

import copy
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Stable agent ids (match plan / admin UI)
AGENT_LOCAL_DB = "local_db_bundle_agent"
AGENT_UCP = "ucp_bundle_agent"
AGENT_MCP = "mcp_bundle_agent"
AGENT_WEATHER = "weather_context_agent"
AGENT_EVENTS = "events_context_agent"
AGENT_RESOURCING = "resourcing_agent"

_BUILTIN_AGENTS: List[Dict[str, Any]] = [
    {
        "id": AGENT_LOCAL_DB,
        "kind": "discovery",
        "enabled_default": True,
        "capabilities": ["products", "bundles"],
        "display_name": "Local inventory",
        "description": "Searches your primary Discovery catalog (PostgreSQL-backed inventory).",
        "category": "Discovery",
        "enabled": True,
        "user_cancellable": False,
        "user_editable": False,
        "skills": {"sources": ["local_db"]},
        "plan_template": ["Context check", "Discovery", "Curate matches"],
        "workflow_order": 10,
    },
    {
        "id": AGENT_UCP,
        "kind": "discovery",
        "enabled_default": True,
        "capabilities": ["products", "ucp"],
        "display_name": "UCP catalog",
        "description": (
            "Looks up products from partner catalogs exposed through the Universal Commerce "
            "Protocol—standardized, machine-readable listings outside your primary inventory."
        ),
        "category": "Discovery",
        "enabled": True,
        "user_cancellable": False,
        "user_editable": False,
        "skills": {"sources": ["ucp"]},
        "plan_template": ["Context check", "UCP discovery", "Relevance filter"],
        "workflow_order": 20,
    },
    {
        "id": AGENT_MCP,
        "kind": "integration",
        "enabled_default": False,
        "capabilities": ["products", "shopify"],
        "display_name": "MCP / Shopify mesh",
        "description": (
            "Adds products from connected partner storefronts (e.g. Shopify) when those "
            "integrations are enabled—an optional mesh on top of local and protocol feeds."
        ),
        "category": "Discovery",
        "enabled": True,
        "user_cancellable": False,
        "user_editable": False,
        "skills": {"sources": ["mcp"]},
        "plan_template": ["Mesh readiness", "Partner catalog scan", "Offer alignment"],
        "workflow_order": 30,
    },
    {
        "id": AGENT_WEATHER,
        "kind": "context",
        "enabled_default": True,
        "capabilities": ["weather", "constraints"],
        "display_name": "Weather context",
        "description": "Fetches current conditions for the requested location.",
        "category": "Context",
        "enabled": True,
        "user_cancellable": True,
        "user_editable": True,
        "skills": {"min_temp_f": None},
        "plan_template": ["Location context", "Conditions lookup", "Comfort readout"],
        "workflow_order": 40,
    },
    {
        "id": AGENT_EVENTS,
        "kind": "context",
        "enabled_default": True,
        "capabilities": ["events", "scheduling"],
        "display_name": "Local events",
        "description": "Surfaces upcoming occasions near the user when events API is configured.",
        "category": "Context",
        "enabled": True,
        "user_cancellable": True,
        "user_editable": True,
        "skills": {"city_boost": True},
        "plan_template": ["Venue context", "Event discovery", "Highlights"],
        "workflow_order": 50,
    },
    {
        "id": AGENT_RESOURCING,
        "kind": "resourcing",
        "enabled_default": False,
        "capabilities": ["alternatives", "sla"],
        "display_name": "Re-sourcing",
        "description": "Checks SLA re-sourcing alternatives and recovery paths for this thread.",
        "category": "Resourcing",
        "enabled": True,
        "user_cancellable": True,
        "user_editable": False,
        "skills": {"check_pending": True},
        "plan_template": ["Thread health", "Alternative inventory", "Recovery narrative"],
        "workflow_order": 60,
    },
]

_DEFAULT_MULTI_AGENT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "workflow_order": [
        AGENT_LOCAL_DB,
        AGENT_UCP,
        AGENT_MCP,
        AGENT_WEATHER,
        AGENT_EVENTS,
        AGENT_RESOURCING,
    ],
    "agents": [],
}


def _get_platform_multi_agent_config() -> Dict[str, Any]:
    try:
        from api.admin import _get_platform_config

        row = _get_platform_config() or {}
        mac = row.get("multi_agent_config")
        if isinstance(mac, dict):
            return mac
        if isinstance(mac, str) and mac.strip():
            try:
                parsed = json.loads(mac)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.debug("multi_agent_config load: %s", e)
    return {}


def _deep_merge_agent(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if k == "skills" and isinstance(v, dict) and isinstance(out.get("skills"), dict):
            merged = dict(out["skills"])
            merged.update(v)
            out["skills"] = merged
        else:
            out[k] = copy.deepcopy(v)
    return out


def get_resolved_registry() -> Dict[str, Any]:
    """
    Returns { enabled, workflow_order, agents: [full agent defs] }.
    Per-agent overrides from multi_agent_config.agents[] keyed by id.
    """
    plat = _get_platform_multi_agent_config()
    enabled = bool(plat.get("enabled", _DEFAULT_MULTI_AGENT_CONFIG["enabled"]))
    workflow = plat.get("workflow_order")
    if not isinstance(workflow, list) or not workflow:
        workflow = list(_DEFAULT_MULTI_AGENT_CONFIG["workflow_order"])

    overrides_by_id: Dict[str, Dict[str, Any]] = {}
    for row in plat.get("agents") or []:
        if isinstance(row, dict) and row.get("id"):
            overrides_by_id[str(row["id"])] = row

    merged_list: List[Dict[str, Any]] = []
    for b in _BUILTIN_AGENTS:
        aid = b["id"]
        ov = overrides_by_id.get(aid, {})
        merged = _deep_merge_agent(b, ov)
        merged_list.append(merged)

    # Allow admin-only agents in config that extend builtins (ignore unknown without builtin)
    known_ids = {a["id"] for a in merged_list}
    for aid, ov in overrides_by_id.items():
        if aid not in known_ids and isinstance(ov, dict) and ov.get("display_name"):
            merged_list.append(_deep_merge_agent({"id": aid, "kind": "discovery", "enabled_default": False, "capabilities": [], "category": "Custom", "enabled": False, "user_cancellable": False, "user_editable": False, "skills": {}, "plan_template": [], "workflow_order": 99, "description": ""}, ov))

    merged_list.sort(key=lambda x: int(x.get("workflow_order") or 0))

    return {
        "enabled": enabled,
        "workflow_order": [str(x) for x in workflow],
        "agents": merged_list,
    }


def registry_for_frontend() -> Dict[str, Any]:
    """Public DTO for Assistant UI and admin (no secrets)."""
    r = get_resolved_registry()
    agents_out = []
    for a in r["agents"]:
        if not a.get("enabled", True):
            continue
        agents_out.append({
            "id": a["id"],
            "name": a.get("display_name") or a["id"],
            "description": (a.get("description") or "")[:500],
            "category": a.get("category") or "General",
            "kind": a.get("kind") or "discovery",
            "enabled_default": bool(a.get("enabled_default", True)),
            "user_cancellable": bool(a.get("user_cancellable", False)),
            "user_editable": bool(a.get("user_editable", False)),
            "skills": a.get("skills") if isinstance(a.get("skills"), (dict, list)) else {},
            "capabilities": a.get("capabilities") or [],
        })
    return {
        "enabled": r["enabled"],
        "workflow_order": r["workflow_order"],
        "agents": agents_out,
    }
