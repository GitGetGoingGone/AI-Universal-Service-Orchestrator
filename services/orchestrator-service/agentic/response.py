"""LLM-generated engagement response - natural user-facing message instead of templated summary."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

RESPONSE_SYSTEM = """You are a friendly shopping assistant. Given the user's message and what was found/done, write a brief, natural 1-3 sentence response to the user.

Be conversational and helpful. Mention key findings (e.g. product categories, count) without listing everything. Invite the user to add items to their bundle or ask for more.
Do NOT use markdown, bullets, or formal structure. Keep it under 100 words.
"""

RESPONSE_SYSTEM_COMPOSITE = """You are a luxury concierge. User asked for [categories]. Two response styles (choose based on fit):

(1) **Detail-gathering flow** — numbered questions for date/time, pickup, trip details, flower type, chocolates, extras.
(2) **Luxury Experience Design** — when categories support a full experience (e.g. limo + flowers + chocolates), present a complete curated plan: phased timing, curated options per category, pro tips, budget guidance, upgrade ideas, personalization hook ('If you tell me occasion, city, budget, style — I'll design a hyper-custom version').

Tone: smooth, elegant, memorable.
**Be flexible**: if user asks for options/prices instead of answering, respond to that. The flow is a guide, not a form.
Do NOT list products. Guide them through structured questions or a curated plan tailored to what they asked for.
"""

RESPONSE_SYSTEM_BROWSE = """User is browsing. Engage conversationally. Ask what they're thinking — special occasion, gifts, exploring options? Do NOT list all categories or products.
"""

RESPONSE_SYSTEM_DISCOVER = """When products found, display as **curated listing** — top 5–6 max. Per entry: name, brief description, **CTA = our payment intent flow** (Add to bundle / Book now — NOT external phone/website). Optional grouping and location-aware intro. Do NOT dump a long raw list.
"""


def _build_context(result: Dict[str, Any]) -> str:
    """Build context string for the LLM from the orchestration result."""
    data = result.get("data") or {}
    intent = data.get("intent") or {}
    products = data.get("products") or {}

    parts = []
    intent_type = intent.get("intent_type", "unknown")
    parts.append(f"Intent: {intent_type}")

    if intent_type in ("checkout", "track", "support"):
        parts.append(f"User needs help with {intent_type}. Direct them appropriately.")
    elif intent_type == "browse":
        parts.append("User is browsing. Engage conversationally. Ask what they're thinking — special occasion, gifts, exploring? Do NOT list all categories.")
    elif intent_type == "discover_composite":
        exp_name = products.get("experience_name", "experience")
        categories = products.get("categories") or []
        cat_names = [c.get("query", "") for c in categories if isinstance(c, dict) and c.get("query")]
        parts.append(
            f"User asked for experience: {exp_name}. Categories they want: {', '.join(cat_names) or 'products'}. "
            "You are a concierge — guide them through a structured flow to gather details for each category. Do NOT list products."
        )
    else:
        product_list = products.get("products") if isinstance(products, dict) else []
        if not product_list and isinstance(products, list):
            product_list = products
        count = products.get("count", len(product_list)) if isinstance(products, dict) else len(product_list)
        if product_list:
            top_products = product_list[:6] if isinstance(product_list, list) else []
            product_entries: List[str] = []
            for p in top_products:
                if isinstance(p, dict):
                    name = p.get("name", "Product")
                    desc = (p.get("description") or "")[:120]
                    price = p.get("price")
                    currency = p.get("currency", "USD")
                    entry = f"{name}"
                    if desc:
                        entry += f" — {desc}"
                    if price is not None:
                        entry += f" ({currency} {price})"
                    product_entries.append(entry)
            location = None
            entities = intent.get("entities") or []
            for e in entities:
                if isinstance(e, dict) and e.get("type") == "location":
                    location = e.get("value")
                    break
            if location:
                parts.append(f"Location context: {location}.")
            parts.append(
                f"Found {count} products. Format as curated listing (top 5–6). Per entry: name, brief description, CTA = Add to bundle / Book now (our payment flow, NOT external phone/website). "
                f"Product data: {'; '.join(product_entries)}"
            )
        else:
            query = intent.get("search_query", "your search")
            parts.append(f"No products found for '{query}'.")

    return " ".join(parts)


def _get_system_prompt_and_max_tokens(intent_type: str) -> Tuple[str, int]:
    """Return (system_prompt, max_tokens) for the given intent."""
    if intent_type == "discover_composite":
        return RESPONSE_SYSTEM_COMPOSITE, 800
    if intent_type == "browse":
        return RESPONSE_SYSTEM_BROWSE, 150
    if intent_type == "discover":
        return RESPONSE_SYSTEM_DISCOVER, 300
    return RESPONSE_SYSTEM, 150


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

    data = result.get("data") or {}
    intent = data.get("intent") or {}
    intent_type = intent.get("intent_type", "unknown")
    system_prompt, max_tokens = _get_system_prompt_and_max_tokens(intent_type)

    context = _build_context(result)
    user_content = f"User said: {user_message[:300]}\n\nWhat we did: {context}\n\nWrite a brief friendly response:"

    try:
        if provider == "azure":
            def _call():
                return client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            response = await asyncio.to_thread(_call)
            text = (response.choices[0].message.content or "").strip()
            return text if text else None

        if provider == "gemini":
            gen_model = client.GenerativeModel(model)
            def _call():
                return gen_model.generate_content(
                    f"{system_prompt}\n\n{user_content}",
                    generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
                )
            resp = await asyncio.to_thread(_call)
            if resp and resp.candidates:
                text = (getattr(resp, "text", None) or "").strip()
                return text if text else None
    except Exception as e:
        logger.warning("Engagement response LLM failed: %s", e)
    return None
