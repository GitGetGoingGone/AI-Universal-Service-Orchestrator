"""Unified discovery interface (Module 1: Scout Engine)."""

from typing import Any, Dict, List, Optional

from packages.shared.discovery import is_browse_query

from db import search_products
from semantic_search import semantic_search


async def search(
    query: str,
    limit: int = 20,
    location: Optional[str] = None,
    partner_id: Optional[str] = None,
    exclude_partner_id: Optional[str] = None,
    use_semantic: bool = True,
) -> List[Dict[str, Any]]:
    """
    Unified product discovery: semantic search when available, else text search.

    - use_semantic=True: Try pgvector first; fallback to text if no results or embeddings unavailable
    - location: Reserved for future geospatial filter (PostGIS)
    """
    if not query or not query.strip():
        return await search_products(query="", limit=limit, partner_id=partner_id, exclude_partner_id=exclude_partner_id)

    # Browse queries: return products without semantic filtering
    if is_browse_query(query):
        return await search_products(query="", limit=limit, partner_id=partner_id, exclude_partner_id=exclude_partner_id)

    if use_semantic:
        results = await semantic_search(
            query=query,
            limit=limit,
            partner_id=partner_id,
            exclude_partner_id=exclude_partner_id,
        )
        if results:
            return results

    # Fallback to text search
    return await search_products(
        query=query,
        limit=limit,
        partner_id=partner_id,
        exclude_partner_id=exclude_partner_id,
    )
