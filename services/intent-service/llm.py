"""Intent resolution via LLM (Azure OpenAI) with action-word stripping fallback."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from config import settings
from packages.shared.discovery import derive_search_query

logger = logging.getLogger(__name__)

INTENT_SYSTEM = """You are an intent classifier for a multi-vendor order platform.
Given a user message, extract:
1. intent_type: one of "discover", "discover_composite", "checkout", "track", "support", "browse"
2. search_query: the product/category to search for (only for discover intent). Use 1-3 key terms. If unclear, use empty string.
3. For discover_composite: search_queries (array of product categories) and experience_name (e.g. "date night")
4. entities: list of {type, value} e.g. [{"type":"location","value":"NYC"}]

Rules:
- "discover" = user wants to find/browse a single product category
- "discover_composite" = user wants a composed experience (e.g. "plan a date night", "birthday party", "picnic"). Decompose into product categories.
- "browse" = generic "show me products" with no specific query
- search_query should be product/category terms only, e.g. "limo", "flowers", "dinner"
- For discover_composite: search_queries = ["flowers","dinner","limo"] for "date night"; experience_name = "date night"
- Strip action words like "wanna book", "looking for", "find me" - keep the product term
- Return valid JSON: {"intent_type":"...","search_query":"...","search_queries":[],"experience_name":"","entities":[],"confidence_score":0.0-1.0}
  Use search_queries and experience_name only for discover_composite.
"""


async def resolve_intent(text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Resolve intent from natural language. Uses Azure OpenAI when configured;
    falls back to heuristics with action-word stripping otherwise.
    When LLM returns bad/empty search_query, uses derive_search_query(text).
    """
    if not text or not text.strip():
        return {
            "intent_type": "browse",
            "search_query": "",
            "entities": [],
            "confidence_score": 0.5,
        }

    if settings.azure_openai_configured:
        try:
            result = await _resolve_via_azure(text)
            # When LLM returns bad/empty search_query for discover intent, use derived
            if result.get("intent_type") == "discover":
                sq = (result.get("search_query") or "").strip()
                if not sq or len(sq) < 2:
                    derived = derive_search_query(text)
                    if derived:
                        result["search_query"] = derived
                        result["confidence_score"] = min(0.9, (result.get("confidence_score") or 0.5) + 0.2)
            return result
        except Exception as e:
            logger.warning("Azure OpenAI intent failed: %s", e)

    return _heuristic_resolve(text)


async def _resolve_via_azure(text: str) -> Dict[str, Any]:
    """Resolve intent via Azure OpenAI."""
    from openai import AzureOpenAI

    client = AzureOpenAI(
        api_key=settings.azure_openai_api_key,
        api_version="2024-02-01",
        azure_endpoint=settings.azure_openai_endpoint.rstrip("/"),
    )

    def _call():
        r = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM},
                {"role": "user", "content": f"User message: {text}"},
            ],
            temperature=0.1,
            max_tokens=200,
        )
        return r

    response = await asyncio.to_thread(_call)
    content = (response.choices[0].message.content or "").strip()

    # Parse JSON from response (may be wrapped in markdown)
    if "```" in content:
        start = content.find("```") + 3
        if content.startswith("```json"):
            start += 4  # skip "json"
        end = content.find("```", start)
        content = content[start:end] if end > start else content

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return _heuristic_resolve(text)

    intent_type = (data.get("intent_type") or "discover").lower()
    if intent_type not in ("discover", "discover_composite", "checkout", "track", "support", "browse"):
        intent_type = "discover"

    out: Dict[str, Any] = {
        "intent_type": intent_type,
        "search_query": (data.get("search_query") or "").strip(),
        "entities": data.get("entities") if isinstance(data.get("entities"), list) else [],
        "confidence_score": float(data.get("confidence_score", 0.8)),
    }
    if intent_type == "discover_composite":
        sq_list = data.get("search_queries")
        if isinstance(sq_list, list) and sq_list:
            out["search_queries"] = [str(q).strip() for q in sq_list if str(q).strip()]
        else:
            out["search_queries"] = []
        out["experience_name"] = (data.get("experience_name") or "").strip() or "experience"
    return out


def _heuristic_resolve(text: str) -> Dict[str, Any]:
    """Heuristic fallback using action-word stripping."""
    text_lower = text.strip().lower()
    if not text_lower or text_lower in ("hi", "hello", "hey", "help"):
        return {
            "intent_type": "browse",
            "search_query": "",
            "entities": [],
            "confidence_score": 0.5,
        }

    # Checkout/track/support keywords
    if any(w in text_lower for w in ("checkout", "pay", "payment", "order")):
        return {"intent_type": "checkout", "search_query": "", "entities": [], "confidence_score": 0.7}
    if any(w in text_lower for w in ("track", "status", "where is", "shipped")):
        return {"intent_type": "track", "search_query": "", "entities": [], "confidence_score": 0.7}
    if any(w in text_lower for w in ("support", "help", "complaint", "refund")):
        return {"intent_type": "support", "search_query": "", "entities": [], "confidence_score": 0.7}

    # discover_composite: only from LLM; heuristic fallback uses single discover + derive
    derived = derive_search_query(text)
    return {
        "intent_type": "discover",
        "search_query": derived if derived else "browse",
        "entities": [],
        "confidence_score": 0.6,
    }
