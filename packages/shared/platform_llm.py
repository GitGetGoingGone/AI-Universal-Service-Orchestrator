"""
Fetch active LLM config from platform_config + llm_providers.
Used by orchestrator, proofing, and other services that need the model from Platform Config.
"""

from typing import Any, Dict, Optional


def get_platform_llm_config(supabase_client) -> Optional[Dict[str, Any]]:
    """
    Fetch active LLM config from platform_config.llm_providers.
    Returns {provider, model, endpoint, api_key, temperature} or None.
    """
    if not supabase_client:
        return None
    try:
        cfg = supabase_client.table("platform_config").select("*").limit(1).execute()
        row = cfg.data[0] if cfg.data else None
        if not row:
            return None
        active_id = row.get("active_llm_provider_id")
        if not active_id:
            return None

        prov = supabase_client.table("llm_providers").select("*").eq("id", active_id).limit(1).execute()
        prov_row = prov.data[0] if prov.data else None
        if not prov_row:
            return None

        api_key = None
        enc = prov_row.get("api_key_encrypted")
        if enc:
            try:
                from packages.shared.encrypt import decrypt_llm_key
                api_key = decrypt_llm_key(enc)
            except Exception:
                pass

        provider = (prov_row.get("provider_type") or "azure").lower()
        if provider == "openai":
            provider = "azure"
        model = prov_row.get("model") or "gpt-4o"
        temp = row.get("llm_temperature")
        temperature = float(temp) if temp is not None else 0.1
        temperature = max(0.0, min(1.0, temperature))

        return {
            "provider": provider,
            "model": model,
            "endpoint": prov_row.get("endpoint"),
            "api_key": api_key,
            "temperature": temperature,
        }
    except Exception:
        return None


def get_platform_image_config(supabase_client) -> Optional[Dict[str, Any]]:
    """
    Fetch active image generation config from platform_config.active_image_provider_id.
    Returns {provider, model, endpoint, api_key} or None.
    """
    if not supabase_client:
        return None
    try:
        cfg = supabase_client.table("platform_config").select("*").limit(1).execute()
        row = cfg.data[0] if cfg.data else None
        if not row:
            return None
        active_id = row.get("active_image_provider_id")
        if not active_id:
            return None

        prov = supabase_client.table("llm_providers").select("*").eq("id", active_id).limit(1).execute()
        prov_row = prov.data[0] if prov.data else None
        if not prov_row:
            return None

        api_key = None
        enc = prov_row.get("api_key_encrypted")
        if enc:
            try:
                from packages.shared.encrypt import decrypt_llm_key
                api_key = decrypt_llm_key(enc)
            except Exception:
                pass

        provider = (prov_row.get("provider_type") or "openai").lower()
        model = prov_row.get("model") or "dall-e-3"
        endpoint = prov_row.get("endpoint")

        return {
            "provider": provider,
            "model": model,
            "endpoint": endpoint,
            "api_key": api_key,
        }
    except Exception:
        return None
