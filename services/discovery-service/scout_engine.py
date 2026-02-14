"""Unified discovery interface (Module 1: Scout Engine)."""

from typing import Any, Dict, List, Optional

from packages.shared.discovery import derive_search_query, is_browse_query
from packages.shared.ranking import sort_products_by_rank

from db import (
    get_active_sponsorships,
    get_partner_ratings_map,
    get_partners_by_ids,
    get_platform_config_ranking,
    search_products,
)
from semantic_search import semantic_search


async def _apply_ranking(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply partner ranking to products. Returns sorted list."""
    if not products:
        return products

    config = await get_platform_config_ranking()
    if not config or not config.get("ranking_enabled", True):
        return products

    product_ids = [str(p.get("id", "")) for p in products if p.get("id")]
    partner_ids = list({str(p.get("partner_id", "")) for p in products if p.get("partner_id")})

    partners_map = await get_partners_by_ids(partner_ids)
    partner_ratings_map = await get_partner_ratings_map(partner_ids)
    active_sponsorships = await get_active_sponsorships(product_ids)

    return sort_products_by_rank(
        products,
        partners_map,
        partner_ratings_map=partner_ratings_map,
        commission_map=None,
        active_sponsorships=active_sponsorships,
        config=config,
    )


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
    - Applies action-word stripping when query looks like full sentence (e.g. "wanna book limo" -> "limo")
    - Applies partner ranking when ranking_enabled in platform_config
    """
    if not query or not query.strip():
        products = await search_products(query="", limit=limit, partner_id=partner_id, exclude_partner_id=exclude_partner_id)
        return await _apply_ranking(products)

    # Browse queries: return products without semantic filtering
    if is_browse_query(query):
        products = await search_products(query="", limit=limit, partner_id=partner_id, exclude_partner_id=exclude_partner_id)
        return await _apply_ranking(products)

    # Action-word stripping: "wanna book limo service" -> "limo"
    if " " in query.strip():
        derived = derive_search_query(query)
        if derived:
            query = derived

    if use_semantic:
        results = await semantic_search(
            query=query,
            limit=limit,
            partner_id=partner_id,
            exclude_partner_id=exclude_partner_id,
        )
        if results:
            return await _apply_ranking(results)

    # Fallback to text search
    products = await search_products(
        query=query,
        limit=limit,
        partner_id=partner_id,
        exclude_partner_id=exclude_partner_id,
    )
    return await _apply_ranking(products)
