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
