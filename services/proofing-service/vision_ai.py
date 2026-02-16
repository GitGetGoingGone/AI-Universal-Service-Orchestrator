"""Vision AI for proof comparison - Pillar 5. Auto-approve based on similarity."""

import logging
from typing import Optional, Tuple

from config import settings

logger = logging.getLogger(__name__)

# Thresholds
AUTO_APPROVE_THRESHOLD = 0.95
HUMAN_REVIEW_THRESHOLD = 0.85


def auto_approve_with_vision_ai(
    proof_image_url: str,
    source_of_truth_url: Optional[str] = None,
) -> Tuple[float, str]:
    """
    Compare proof image with source of truth. Returns (similarity_score, recommendation).
    recommendation: 'auto_approve' | 'human_review' | 'reject'
    """
    if not proof_image_url:
        return (0.0, "reject")

    if not _vision_configured():
        return (0.0, "reject")

    try:
        score = _compare_images(proof_image_url, source_of_truth_url)
        if score >= AUTO_APPROVE_THRESHOLD:
            return (score, "auto_approve")
        if score >= HUMAN_REVIEW_THRESHOLD:
            return (score, "human_review")
        return (score, "reject")
    except Exception as e:
        logger.warning("Vision AI comparison failed: %s", e)
        return (0.0, "reject")


def _vision_configured() -> bool:
    """Vision uses Platform Config LLM or OPENAI_API_KEY fallback."""
    if settings.openai_api_key:
        return True
    try:
        from db import get_supabase
        from packages.shared.platform_llm import get_platform_llm_config
        client = get_supabase()
        cfg = get_platform_llm_config(client) if client else None
        return bool(cfg and cfg.get("api_key"))
    except Exception:
        return False


def _compare_images(proof_url: str, source_url: Optional[str]) -> float:
    """Use Platform Config LLM or OpenAI Vision to compare images. Returns 0-1 similarity score."""
    try:
        from openai import OpenAI
        from db import get_supabase
        from packages.shared.platform_llm import get_platform_llm_config

        client = None
        model = "gpt-4o"

        supabase = get_supabase()
        cfg = get_platform_llm_config(supabase) if supabase else None
        if cfg and cfg.get("api_key"):
            model = cfg.get("model") or "gpt-4o"
            provider = cfg.get("provider", "azure")
            if provider == "openrouter":
                client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=cfg["api_key"])
            elif provider == "custom" and cfg.get("endpoint"):
                base = cfg["endpoint"].rstrip("/")
                if not base.endswith("/v1"):
                    base = f"{base}/v1"
                client = OpenAI(base_url=base, api_key=cfg["api_key"])
            elif provider in ("azure", "openai") and cfg.get("endpoint"):
                from openai import AzureOpenAI
                client = AzureOpenAI(
                    api_key=cfg["api_key"],
                    api_version="2024-02-15-preview",
                    azure_endpoint=cfg["endpoint"].rstrip("/"),
                )
            else:
                client = OpenAI(api_key=cfg["api_key"])

        if not client and settings.openai_api_key:
            client = OpenAI(api_key=settings.openai_api_key)

        if not client:
            return 0.0

        content = [
            {"type": "text", "text": "Compare these two images. Return ONLY a number from 0 to 1 indicating visual similarity (1=identical). No other text."},
            {"type": "image_url", "image_url": {"url": proof_url}},
        ]
        if source_url:
            content.append({"type": "image_url", "image_url": {"url": source_url}})
        else:
            content[0]["text"] = "Rate this image's quality and completeness for a product proof from 0 to 1. Return ONLY the number."

        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            max_tokens=10,
        )
        text = (resp.choices[0].message.content or "0").strip()
        score = float(text) if text.replace(".", "").isdigit() else 0.0
        return max(0.0, min(1.0, score))
    except Exception as e:
        logger.warning("Vision compare failed: %s", e)
        return 0.0
