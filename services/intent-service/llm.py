"""Intent resolution via heuristics (action-word stripping). LLM config is in Platform Config."""

import logging
from typing import Any, Dict, List, Optional

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
- When last_suggestion is provided: user may be refining (e.g. "I don't want flowers, add a movie", "no flowers", "add chocolates"). Interpret as discover or discover_composite with updated search_queries (remove rejected categories, add requested ones).
- search_query should be product/category terms only, e.g. "limo", "flowers", "dinner"
- For discover_composite: search_queries = ["flowers","dinner","limo"] for "date night"; experience_name = "date night"
- Strip action words like "wanna book", "looking for", "find me" - keep the product term
- Return valid JSON: {"intent_type":"...","search_query":"...","search_queries":[],"experience_name":"","entities":[],"confidence_score":0.0-1.0}
  Use search_queries and experience_name only for discover_composite.
"""


async def resolve_intent(text: str, user_id: Optional[str] = None, last_suggestion: Optional[str] = None) -> Dict[str, Any]:
    """
    Resolve intent from natural language using heuristics (action-word stripping).
    """
    if not text or not text.strip():
        return {
            "intent_type": "browse",
            "search_query": "",
            "entities": [],
            "confidence_score": 0.5,
        }

    return _heuristic_resolve(text)


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
