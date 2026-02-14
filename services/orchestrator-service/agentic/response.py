"""LLM-generated engagement response - natural user-facing message instead of templated summary."""

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

RESPONSE_SYSTEM = """You are a friendly shopping assistant. Given the user's message and what was found/done, write a brief, natural 1-3 sentence response to the user.

Be conversational and helpful. Mention key findings (e.g. product categories, count) without listing everything. Invite the user to add items to their bundle or ask for more.
Do NOT use markdown, bullets, or formal structure. Keep it under 100 words.
"""


def _build_context(result: Dict[str, Any]) -> str:
    """Build context string for the LLM from the orchestration result."""
    data = result.get("data") or {}
    intent = data.get("intent") or {}
    products = data.get("products") or {}

    parts = []
    intent_type = intent.get("intent_type", "unknown")
    parts.append(f"Intent: {intent_type}")

    if intent_type in ("checkout", "track", "support", "browse"):
        parts.append(f"User needs help with {intent_type}. Direct them appropriately.")
    elif intent_type == "discover_composite":
        exp_name = products.get("experience_name", "experience")
        categories = products.get("categories") or []
        count = products.get("count", 0)
        cat_names = [c.get("query", "") for c in categories if c.get("query")]
        parts.append(f"Experience: {exp_name}. Categories: {', '.join(cat_names)}. Found {count} products total.")
    else:
        product_list = products.get("products") if isinstance(products, dict) else []
        if not product_list and isinstance(products, list):
            product_list = products
        count = products.get("count", len(product_list)) if isinstance(products, dict) else len(product_list)
        if product_list:
            names = [p.get("name", "Product") for p in product_list[:5] if isinstance(p, dict)]
            parts.append(f"Found {count} products. Examples: {', '.join(names)}")
        else:
            query = intent.get("search_query", "your search")
            parts.append(f"No products found for '{query}'.")

    return " ".join(parts)


async def generate_engagement_response(
    user_message: str,
    result: Dict[str, Any],
    llm_config: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Generate a natural, engaging response using the LLM.
    Returns None on failure (caller should fall back to templated summary).
    """
    if result.get("error"):
        return None

    if llm_config is None:
        from api.admin import get_llm_config
        llm_config = get_llm_config()

    from .planner import _get_planner_client_for_config
    provider, client = _get_planner_client_for_config(llm_config)
    if not client:
        return None

    model = llm_config.get("model") or ("gpt-4o" if provider == "azure" else "gemini-1.5-flash")
    temperature = min(0.7, float(llm_config.get("temperature", 0.1)) + 0.3)  # Slightly more creative for engagement

    context = _build_context(result)
    user_content = f"User said: {user_message[:300]}\n\nWhat we did: {context}\n\nWrite a brief friendly response:"

    try:
        if provider == "azure":
            def _call():
                return client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": RESPONSE_SYSTEM},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=temperature,
                    max_tokens=150,
                )
            response = await asyncio.to_thread(_call)
            text = (response.choices[0].message.content or "").strip()
            return text if text else None

        if provider == "gemini":
            gen_model = client.GenerativeModel(model)
            def _call():
                return gen_model.generate_content(
                    f"{RESPONSE_SYSTEM}\n\n{user_content}",
                    generation_config={"temperature": temperature, "max_output_tokens": 150},
                )
            resp = await asyncio.to_thread(_call)
            if resp and resp.candidates:
                text = (getattr(resp, "text", None) or "").strip()
                return text if text else None
    except Exception as e:
        logger.warning("Engagement response LLM failed: %s", e)
    return None
