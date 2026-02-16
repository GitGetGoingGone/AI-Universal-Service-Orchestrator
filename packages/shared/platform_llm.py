"""
Fetch active LLM config from platform_config + llm_providers.
Used by orchestrator, proofing, intent, hybrid, and other services that need the model from Platform Config.
"""

from typing import Any, Dict, Optional, Tuple


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


def get_llm_chat_client(llm_config: Dict[str, Any]) -> Tuple[Optional[str], Any]:
    """
    Create chat client from platform LLM config.
    Returns (provider, client) where provider is 'azure'|'openrouter'|'custom'|'gemini', client is OpenAI or genai.
    Returns (None, None) when not configured.
    """
    if not llm_config:
        return (None, None)
    cfg = llm_config or {}
    preferred = (cfg.get("provider") or "azure").lower()
    if preferred == "openai":
        preferred = "azure"
    api_key = cfg.get("api_key")
    endpoint = cfg.get("endpoint")

    try:
        if preferred == "openrouter" and api_key:
            from openai import OpenAI
            return ("openrouter", OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key))

        if preferred == "custom" and endpoint and api_key:
            from openai import OpenAI
            base = endpoint.rstrip("/")
            if not base.endswith("/v1"):
                base = f"{base}/v1"
            return ("custom", OpenAI(base_url=base, api_key=api_key))

        if preferred == "gemini" and api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            return ("gemini", genai)

        if preferred in ("azure", "openai") and api_key:
            from openai import OpenAI, AzureOpenAI
            if endpoint:
                return ("azure", AzureOpenAI(
                    api_key=api_key,
                    api_version="2024-02-01",
                    azure_endpoint=endpoint.rstrip("/"),
                ))
            return ("openai", OpenAI(api_key=api_key))
    except Exception:
        pass
    return (None, None)


def get_model_interaction_prompt(supabase_client, interaction_type: str) -> Optional[Dict[str, Any]]:
    """
    Fetch prompt config for interaction_type from model_interaction_prompts.
    Returns {system_prompt, enabled, max_tokens} or None.
    system_prompt may be null (caller uses code default).
    """
    if not supabase_client:
        return None
    try:
        r = supabase_client.table("model_interaction_prompts").select(
            "system_prompt, enabled, max_tokens"
        ).eq("interaction_type", interaction_type).limit(1).execute()
        row = r.data[0] if r.data else None
        if not row:
            return None
        return {
            "system_prompt": row.get("system_prompt"),
            "enabled": row.get("enabled", True),
            "max_tokens": row.get("max_tokens") or 500,
        }
    except Exception:
        return None
