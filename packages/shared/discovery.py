"""Shared discovery utilities: browse detection, search query derivation, action-word stripping."""

import re
from typing import Set

# Browse queries return catalog without semantic/text filter (sample products)
BROWSE_QUERIES: Set[str] = {
    "sample",
    "samples",
    "demo",
    "please",
    "show",
    "browse",
    "products",
    "items",
    "what",
    "anything",
    "something",
    "whatever",
    "catalog",
    "list",
    "all",
}

# Action/filler words to strip when deriving search query from raw message.
_ACTION_FILLER_WORDS: Set[str] = {
    "i", "me", "my", "want", "wanna", "need", "looking", "for", "find", "get",
    "search", "book", "booked", "booking", "show", "give", "please", "something",
    "anything", "the", "a", "an", "to", "for", "service", "services", "help",
    "like", "would", "could", "can", "some", "about", "around", "near", "nearby",
    "close", "cheap", "affordable", "good", "best", "top", "recommend", "suggest",
    "offer", "offers", "provide", "sell", "buy", "order", "reserve", "rent", "hire",
    "delivery", "deliver", "what", "you", "got", "items", "products", "options",
}


def is_browse_query(query: str) -> bool:
    """Return True if query is a browse term (show catalog without filter)."""
    if not query or not isinstance(query, str):
        return True
    q = query.strip().lower()
    return q in BROWSE_QUERIES or not q


def derive_search_query(text: str) -> str:
    """Strip action/filler words from raw message to derive a product-focused search query."""
    if not text or not isinstance(text, str):
        return ""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    if not normalized:
        return ""
    tokens = re.findall(r"[a-z0-9]+", normalized)
    kept = [t for t in tokens if t not in _ACTION_FILLER_WORDS and len(t) > 1]
    return " ".join(kept) if kept else ""


def fallback_search_query(text: str) -> str:
    """Derive search query when Intent service is unavailable."""
    derived = derive_search_query(text)
    if derived:
        return derived
    return (text or "").strip()[:50] or "browse"
