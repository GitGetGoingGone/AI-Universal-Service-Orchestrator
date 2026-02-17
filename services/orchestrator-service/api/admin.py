"""Platform admin: kill switch, SLA config, test interaction."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import settings
from db import get_supabase

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

# Default sample messages per interaction type for test
DEFAULT_SAMPLE_MESSAGES: Dict[str, str] = {
    "intent": "Plan a date night",
    "hybrid_response": "Where is my order?",
    "planner": "User message: Plan a date night. Current state: { iteration: 0, last_tool_result: null }. What is your next action?",
    "engagement_discover": "User said: show me flowers. Found 3 products: Red Roses ($49), Tulips ($35), Sunflowers ($29). Write a brief friendly response.",
    "engagement_browse": "User is browsing with no specific query. Engage them conversationally.",
    "engagement_discover_composite": "User asked for date night. Categories: flowers, dinner, movies. Found: Red Roses. No dinner or movies in catalog. Write a helpful response.",
    "engagement_default": "User said: I want to checkout. What we did: Found their bundle with 2 items. Write a brief response.",
}

_llm_config_cache: Optional[Tuple[float, Dict[str, Any]]] = None
LLM_CACHE_TTL_SEC = 60


class KillSwitchBody(BaseModel):
    active: bool = Field(..., description="True to activate, False to deactivate")
    reason: Optional[str] = Field(None, description="Reason for kill switch")
    activated_by: Optional[str] = Field(None, description="User ID of admin")


class TestInteractionBody(BaseModel):
    interaction_type: str = Field(..., description="e.g. intent, planner, engagement_discover")
    sample_user_message: Optional[str] = Field(None, description="Override default sample message")
    system_prompt_override: Optional[str] = Field(None, description="Use this prompt instead of saved (for testing edits)")


def _get_platform_config() -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("platform_config").select("*").limit(1).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def _update_platform_config(updates: Dict[str, Any]) -> bool:
    client = get_supabase()
    if not client:
        return False
    try:
        cfg = _get_platform_config()
        if cfg:
            client.table("platform_config").update(updates).eq("id", cfg["id"]).execute()
        else:
            client.table("platform_config").insert(updates).execute()
        return True
    except Exception:
        return False


def get_llm_config() -> Dict[str, Any]:
    """Get LLM config from platform_config or llm_providers with 60s TTL cache. Used by planner."""
    global _llm_config_cache
    now = time.time()
    if _llm_config_cache and (now - _llm_config_cache[0]) < LLM_CACHE_TTL_SEC:
        return _llm_config_cache[1]

    cfg = _get_platform_config()
    active_id = (cfg or {}).get("active_llm_provider_id")

    if active_id:
        client = get_supabase()
        if client:
            try:
                r = client.table("llm_providers").select("*").eq("id", active_id).limit(1).execute()
                row = r.data[0] if r.data else None
                if row:
                    api_key = None
                    enc = row.get("api_key_encrypted")
                    if enc:
                        try:
                            from packages.shared.encrypt import decrypt_llm_key
                            api_key = decrypt_llm_key(enc)
                        except Exception:
                            pass
                    provider = (row.get("provider_type") or "azure").lower()
                    if provider == "openai":
                        provider = "azure"
                    temp = (cfg or {}).get("llm_temperature")
                    temperature = float(temp) if temp is not None else 0.1
                    temperature = max(0.0, min(1.0, temperature))
                    result = {
                        "provider": provider,
                        "model": row.get("model") or "gpt-4o",
                        "temperature": temperature,
                        "endpoint": row.get("endpoint"),
                        "api_key": api_key,
                    }
                    _llm_config_cache = (now, result)
                    return result
            except Exception:
                pass

    provider = (cfg or {}).get("llm_provider") or "azure"
    if provider == "openai":
        provider = "azure"
    model = (cfg or {}).get("llm_model") or (
        "gpt-4o"
    )
    temp = (cfg or {}).get("llm_temperature")
    temperature = float(temp) if temp is not None else 0.1
    temperature = max(0.0, min(1.0, temperature))
    result = {"provider": provider, "model": model, "temperature": temperature}
    _llm_config_cache = (now, result)
    return result


@router.post("/kill-switch")
async def kill_switch(body: KillSwitchBody) -> Dict[str, Any]:
    """
    Activate or deactivate platform kill switch.
    When active: blocks new orders, checkout, standing intents.
    Logs to kill_switch_events.
    """
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database unavailable")

    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "kill_switch_active": body.active,
        "kill_switch_reason": body.reason,
        "kill_switch_activated_at": now if body.active else None,
        "updated_at": now,
    }
    _update_platform_config(updates)

    client.table("kill_switch_events").insert({
        "activated": body.active,
        "reason": body.reason,
        "activated_by": body.activated_by,
        "metadata": {},
    }).execute()

    return {
        "kill_switch_active": body.active,
        "reason": body.reason,
        "message": "Platform paused. New orders blocked." if body.active else "Platform resumed.",
    }


@router.get("/kill-switch")
async def get_kill_switch_status() -> Dict[str, Any]:
    """Get current kill switch status."""
    cfg = _get_platform_config()
    if not cfg:
        return {"kill_switch_active": False, "reason": None}
    return {
        "kill_switch_active": cfg.get("kill_switch_active", False),
        "reason": cfg.get("kill_switch_reason"),
        "activated_at": cfg.get("kill_switch_activated_at"),
    }


@router.post("/test-interaction")
async def test_interaction(body: TestInteractionBody) -> Dict[str, Any]:
    """
    Test an interaction with the configured model. Sends the interaction's system prompt
    plus a sample user message, returns the model response. Use to verify connection
    and tweak prompts.
    """
    llm_config = get_llm_config()
    if not llm_config or not llm_config.get("api_key"):
        raise HTTPException(status_code=503, detail="No LLM configured or API key missing.")

    from packages.shared.platform_llm import get_llm_chat_client, get_model_interaction_prompt

    client = get_supabase()
    prompt_cfg = get_model_interaction_prompt(client, body.interaction_type) if client else None
    system_prompt = body.system_prompt_override if body.system_prompt_override is not None else (
        (prompt_cfg.get("system_prompt") if prompt_cfg else None) or ""
    )
    max_tokens = prompt_cfg.get("max_tokens", 500) if prompt_cfg else 500

    user_message = body.sample_user_message or DEFAULT_SAMPLE_MESSAGES.get(
        body.interaction_type, "Test message"
    )

    provider, chat_client = get_llm_chat_client(llm_config)
    if not chat_client:
        raise HTTPException(status_code=503, detail="Could not create LLM client for provider.")

    model = llm_config.get("model") or "gpt-4o"
    temperature = min(0.3, float(llm_config.get("temperature", 0.1)))

    try:
        if provider in ("azure", "openrouter", "custom", "openai"):
            def _call():
                return chat_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            response = await asyncio.to_thread(_call)
            text = (response.choices[0].message.content or "").strip()
            return {"response": text, "model": model, "interaction_type": body.interaction_type}

        if provider == "gemini":
            gen_model = chat_client.GenerativeModel(model)
            def _call():
                return gen_model.generate_content(
                    f"{system_prompt or 'You are a helpful assistant.'}\n\nUser: {user_message}",
                    generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
                )
            resp = await asyncio.to_thread(_call)
            if resp and resp.candidates:
                text = (getattr(resp, "text", None) or "").strip()
                return {"response": text, "model": model, "interaction_type": body.interaction_type}
            raise HTTPException(status_code=502, detail="Gemini returned no response")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model call failed: {str(e)}")

    raise HTTPException(status_code=503, detail="Unsupported provider for test")


@router.get("/platform-config")
async def get_platform_config() -> Dict[str, Any]:
    """Get platform config (SLA, buffer, approval thresholds)."""
    cfg = _get_platform_config()
    if not cfg:
        return {}
    return {
        "sla_response_time_ms": cfg.get("sla_response_time_ms", 3000),
        "sla_availability_pct": float(cfg.get("sla_availability_pct", 99.5)),
        "requires_human_approval_over_cents": cfg.get("requires_human_approval_over_cents", 20000),
        "delivery_buffer_minutes": cfg.get("delivery_buffer_minutes", 15),
        "kill_switch_active": cfg.get("kill_switch_active", False),
    }


def is_kill_switch_active() -> bool:
    """Check if kill switch is active. Used by checkout, standing intents."""
    cfg = _get_platform_config()
    return bool(cfg and cfg.get("kill_switch_active"))


def get_delivery_buffer_minutes() -> int:
    """Get delivery window buffer (e.g. +15 min)."""
    cfg = _get_platform_config()
    return int(cfg.get("delivery_buffer_minutes", 15) if cfg else 15)
