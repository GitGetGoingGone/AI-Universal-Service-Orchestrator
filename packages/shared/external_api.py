"""
Fetch external API config from platform_config + external_api_providers.
Used by orchestrator engagement tools (web search, weather, events).
"""

from typing import Any, Dict, Optional


def get_external_api_config(supabase_client, api_type: str) -> Optional[Dict[str, Any]]:
    """
    Fetch active external API config for api_type from platform_config.
    Returns {base_url, api_key, extra_config} or None when not configured.
    """
    if not supabase_client:
        return None
    try:
        cfg = supabase_client.table("platform_config").select("active_external_api_ids").limit(1).execute()
        row = cfg.data[0] if cfg.data else None
        if not row:
            return None
        active_ids = row.get("active_external_api_ids") or {}
        if not isinstance(active_ids, dict):
            return None
        provider_id = active_ids.get(api_type)
        if not provider_id:
            return None

        r = supabase_client.table("external_api_providers").select("*").eq("id", provider_id).eq("enabled", True).limit(1).execute()
        prov = r.data[0] if r.data else None
        if not prov:
            return None

        api_key = None
        enc = prov.get("api_key_encrypted")
        if enc:
            try:
                from packages.shared.encrypt import decrypt_llm_key
                api_key = decrypt_llm_key(enc)
            except Exception:
                pass

        return {
            "base_url": (prov.get("base_url") or "").rstrip("/"),
            "api_key": api_key,
            "extra_config": prov.get("extra_config") or {},
        }
    except Exception:
        return None
