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
    return bool(
        settings.openai_api_key or (settings.azure_openai_endpoint and settings.azure_openai_api_key)
    )


def _compare_images(proof_url: str, source_url: Optional[str]) -> float:
    """Use OpenAI Vision to compare images. Returns 0-1 similarity score."""
    try:
        if settings.azure_openai_endpoint and settings.azure_openai_api_key:
            from openai import AzureOpenAI
            client = AzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version="2024-02-15-preview",
                azure_endpoint=settings.azure_openai_endpoint,
            )
            model = settings.azure_openai_deployment
        else:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            model = "gpt-4o"

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
