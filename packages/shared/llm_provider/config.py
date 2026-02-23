"""Config for LLM provider: env-based (LLM_PRIMARY, LLM_FALLBACK, OSS_ENDPOINT, OPENAI_API_KEY)."""

import os
from typing import Any, Dict, Optional


def get_llm_provider_config() -> Dict[str, Any]:
    """
    Read LLM provider config from environment.
    - LLM_PRIMARY: "oss" | "openai" (default "oss" when OSS_ENDPOINT set, else "openai")
    - LLM_FALLBACK: "openai" | "oss" | "" (optional)
    - OSS_ENDPOINT: OpenAI-compatible endpoint for self-hosted (e.g. Groq, RunPod)
    - OSS_API_KEY: Optional API key for OSS endpoint
    - OSS_MODEL: Model name for OSS (default from endpoint or "gpt-oss-20b" for Groq)
    - OPENAI_API_KEY: OpenAI API key for fallback
    - OPENAI_MODEL: Model for fallback (default "gpt-4o")
    - LLM_TIMEOUT_SEC: Request timeout (default 30)
    - LLM_MAX_RETRIES: Retries before fallback (default 1)
    """
    primary = (os.getenv("LLM_PRIMARY") or "").strip().lower()
    fallback = (os.getenv("LLM_FALLBACK") or "").strip().lower()
    oss_endpoint = (os.getenv("OSS_ENDPOINT") or "").strip().rstrip("/")
    oss_key = (os.getenv("OSS_API_KEY") or os.getenv("GROQ_API_KEY") or "").strip()
    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()

    # Default primary: oss if OSS_ENDPOINT set, else openai
    if not primary:
        primary = "oss" if oss_endpoint else "openai"
    if primary not in ("oss", "openai"):
        primary = "openai"

    if fallback and fallback not in ("oss", "openai"):
        fallback = ""

    timeout = 30
    try:
        t = os.getenv("LLM_TIMEOUT_SEC")
        if t:
            timeout = max(5, min(120, int(t)))
    except ValueError:
        pass

    retries = 1
    try:
        r = os.getenv("LLM_MAX_RETRIES")
        if r:
            retries = max(0, min(3, int(r)))
    except ValueError:
        pass

    return {
        "LLM_PRIMARY": primary,
        "LLM_FALLBACK": fallback or None,
        "OSS_ENDPOINT": oss_endpoint or None,
        "OSS_API_KEY": oss_key or None,
        "OSS_MODEL": (os.getenv("OSS_MODEL") or os.getenv("GROQ_MODEL") or "openai/gpt-oss-20b").strip(),
        "OPENAI_API_KEY": openai_key or None,
        "OPENAI_MODEL": (os.getenv("OPENAI_MODEL") or "gpt-4o").strip(),
        "LLM_TIMEOUT_SEC": timeout,
        "LLM_MAX_RETRIES": retries,
    }
