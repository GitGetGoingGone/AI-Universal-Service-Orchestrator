"""
Discovery service constants and helpers.

Centralizes browse/sample query handling so Discovery returns products
without text filtering when the user intent is "show me what you have"
rather than a specific product search.
"""

# Queries that mean "browse" or "show sample" - Discovery returns products without text filter.
# Single source of truth; add new terms here as needed.
BROWSE_QUERIES = frozenset({
    "please", "hi", "hello", "hey", "sample", "demo", "general", "anything",
    "something", "browse", "show", "return", "brief", "small", "set",
})


def is_browse_query(query: str) -> bool:
    """
    True if query indicates browse/sample intent (no specific product search).
    Discovery should return products without text filtering.
    """
    if not query or not query.strip():
        return True
    q = query.strip().lower()
    if q in BROWSE_QUERIES:
        return True
    if len(q) < 4:
        return True
    return False


# Product keywords for local fallback when Intent service is unavailable
_PRODUCT_KEYWORDS = frozenset({
    "flowers", "chocolates", "chocolate", "gifts", "gift", "cakes", "cake",
    "bouquet", "plants", "candy", "candies", "wine", "spa", "massage",
})


def fallback_search_query(text: str) -> str:
    """
    Extract a search query from raw text when Intent service is unavailable.
    Returns "browse" for generic text; otherwise first product keyword found.
    """
    import re
    t = (text or "").strip().lower()
    if not t:
        return "browse"
    for kw in _PRODUCT_KEYWORDS:
        if kw in t:
            return kw
    words = re.findall(r"\b\w{4,}\b", t)
    for w in words:
        if w not in BROWSE_QUERIES:
            return w
    return "browse"
