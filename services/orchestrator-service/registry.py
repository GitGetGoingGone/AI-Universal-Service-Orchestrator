"""RegistryDriver: load Business Agent URLs from internal_agent_registry (Supabase) or config."""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

from config import settings
from db import get_supabase

logger = logging.getLogger(__name__)


@dataclass
class AgentEntry:
    """One Business Agent from the registry."""
    base_url: str
    display_name: str
    slug: str  # Stable slug for masking (e.g. uso_{slug}_{id})


def _display_name_to_slug(display_name: str) -> str:
    """Derive a stable slug from display_name (e.g. 'Discovery Service' -> 'discovery')."""
    if not display_name or not str(display_name).strip():
        return "agent"
    s = str(display_name).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_") or "agent"
    return s[:64]


def get_agents(capability: Optional[str] = None) -> List[AgentEntry]:
    """
    Load Business Agents from internal_agent_registry (Supabase).
    When capability is set, return only agents that have that capability.
    Returns list of AgentEntry (base_url, display_name, slug). Slug is used for ID masking (uso_{slug}_{id}).
    When DB is empty or not configured, falls back to single discovery_service_url so existing behavior is preserved.
    """
    client = get_supabase()
    if client:
        try:
            q = (
                client.table("internal_agent_registry")
                .select("base_url, display_name, capability")
                .eq("enabled", True)
            )
            if capability and str(capability).strip():
                q = q.eq("capability", str(capability).strip())
            r = q.execute()
            rows = r.data or []
            if rows:
                seen: set = set()
                out: List[AgentEntry] = []
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    base_url = (row.get("base_url") or "").strip().rstrip("/")
                    if not base_url or base_url in seen:
                        continue
                    seen.add(base_url)
                    display_name = (row.get("display_name") or "Agent").strip() or "Agent"
                    slug = _display_name_to_slug(display_name)
                    out.append(AgentEntry(base_url=base_url, display_name=display_name, slug=slug))
                if out:
                    return out
        except Exception as e:
            logger.warning("RegistryDriver: failed to load from internal_agent_registry: %s", e)

    # Fallback: single Discovery service from config (existing behavior)
    url = (getattr(settings, "discovery_service_url", None) or "").strip().rstrip("/")
    if url:
        return [AgentEntry(base_url=url, display_name="Discovery Service", slug="discovery")]
    return []


def get_capabilities() -> List[str]:
    """Return distinct capability values from the registry (for unified manifest)."""
    client = get_supabase()
    if not client:
        return []
    try:
        r = client.table("internal_agent_registry").select("capability").eq("enabled", True).execute()
        rows = r.data or []
        caps = set()
        for row in rows:
            if isinstance(row, dict) and row.get("capability"):
                caps.add(str(row["capability"]).strip())
        return sorted(caps)
    except Exception as e:
        logger.warning("RegistryDriver: failed to load capabilities: %s", e)
        return []
