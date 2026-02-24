"""Unified discovery interface (Module 1: Scout Engine)."""

from typing import Any, Dict, List, Optional

from config import settings
from packages.shared.discovery import derive_search_query, is_browse_query
from packages.shared.discovery_aggregator import (
    DiscoveryAggregator,
    LocalDBDriver,
    MCPDriver,
    UCPManifestDriver,
)
from packages.shared.ranking import sort_products_by_rank

from db import (
    get_active_sponsorships,
    get_admin_orchestration_settings,
    get_composite_discovery_config,
    get_internal_agent_urls,
    get_partner_ratings_map,
    get_partners_by_ids,
    get_platform_config_ranking,
    search_products,
)
from semantic_search import semantic_search


async def _apply_ranking(
    products: List[Dict[str, Any]],
    experience_tag: Optional[str] = None,
    experience_tag_boost_amount: float = 0.2,
) -> List[Dict[str, Any]]:
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
        experience_tag_boost=experience_tag,
        experience_tag_boost_amount=experience_tag_boost_amount,
    )


def _sort_products_by_slice(
    products: List[Dict[str, Any]],
    sort_type: str,
    partners_map: Dict[str, Dict[str, Any]],
    partner_ratings_map: Dict[str, float],
    active_sponsorships: set,
) -> List[Dict[str, Any]]:
    """Sort products by slice type. Returns new list."""
    if not products:
        return []
    key = sort_type.lower()
    if key == "price_desc":
        return sorted(products, key=lambda p: (-float(p.get("price") or 0), str(p.get("created_at", ""))))
    if key == "price_asc":
        return sorted(products, key=lambda p: (float(p.get("price") or 0), str(p.get("created_at", ""))))
    if key == "rating":
        def _rating_score(p):
            pid = str(p.get("partner_id", ""))
            r = partner_ratings_map.get(pid)
            return (-(r if r is not None else 0), str(p.get("created_at", "")))
        return sorted(products, key=_rating_score)
    if key == "popularity":
        return sorted(products, key=lambda p: (-int(p.get("sold_count") or 0), str(p.get("created_at", ""))))
    if key == "sponsored":
        def _sponsored_first(p):
            pid = str(p.get("id", ""))
            return (0 if pid in active_sponsorships else 1, str(p.get("created_at", "")))
        return sorted(products, key=_sponsored_first)
    if key == "recent":
        return sorted(products, key=lambda p: str(p.get("created_at", "")), reverse=True)
    return products


async def _apply_product_mix(
    products: List[Dict[str, Any]],
    product_mix: List[Dict[str, Any]],
    limit: int,
    partners_map: Dict[str, Dict[str, Any]],
    partner_ratings_map: Dict[str, float],
    active_sponsorships: set,
) -> List[Dict[str, Any]]:
    """
    Compose products from slices by pct. Dedupe (first occurrence wins).
    product_mix: [{sort, limit, pct}, ...]; pct should sum to 100.
    """
    if not products or not product_mix or limit <= 0:
        return products[:limit] if products else []

    total_pct = sum(s.get("pct", 0) for s in product_mix)
    if total_pct <= 0:
        return products[:limit]

    seen: set = set()
    out: List[Dict[str, Any]] = []
    slots_per_slice = [(s, max(1, int(round(limit * (s.get("pct", 0) / total_pct))))) for s in product_mix]

    for slice_cfg, take_count in slots_per_slice:
        sort_type = slice_cfg.get("sort", "recent")
        slice_limit = int(slice_cfg.get("limit", 10))
        sorted_prods = _sort_products_by_slice(
            products, sort_type, partners_map, partner_ratings_map, active_sponsorships
        )
        taken = 0
        for p in sorted_prods[:slice_limit]:
            if taken >= take_count:
                break
            pid = str(p.get("id", ""))
            if pid not in seen:
                seen.add(pid)
                out.append(p)
                taken += 1

    # Fill remaining with any not yet included
    for p in products:
        if len(out) >= limit:
            break
        pid = str(p.get("id", ""))
        if pid not in seen:
            seen.add(pid)
            out.append(p)
    return out[:limit]


async def _fetch_via_aggregator(
    query: str,
    fetch_limit: int,
    partner_id: Optional[str],
    exclude_partner_id: Optional[str],
    experience_tag: Optional[str] = None,
    experience_tags: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Fetch via DiscoveryAggregator (LocalDB + optional UCP from private registry) with timeout."""
    admin = await get_admin_orchestration_settings()
    timeout_ms = 5000
    if admin and isinstance(admin.get("discovery_timeout_ms"), (int, float)):
        timeout_ms = int(admin["discovery_timeout_ms"])
    local_driver = LocalDBDriver(search_products)
    ucp_driver = None
    internal_urls = await get_internal_agent_urls()
    if internal_urls:
        async def _get_partner_urls():
            return internal_urls
        ucp_driver = UCPManifestDriver(get_partner_manifest_urls=_get_partner_urls)
    aggregator = DiscoveryAggregator(
        local_db_driver=local_driver,
        ucp_driver=ucp_driver,
        mcp_driver=None,
        timeout_ms=timeout_ms,
    )
    ucp_products = await aggregator.search(
        query=query,
        limit=fetch_limit,
        partner_id=partner_id,
        exclude_partner_id=exclude_partner_id,
        experience_tag=experience_tag,
        experience_tags=experience_tags,
    )
    return [p.to_dict() for p in ucp_products]


async def _fetch_and_rank(
    query: str,
    limit: int,
    partner_id: Optional[str],
    exclude_partner_id: Optional[str],
    use_semantic: bool,
    experience_tag: Optional[str] = None,
    experience_tags: Optional[List[str]] = None,
    experience_tag_boost_amount: float = 0.2,
) -> List[Dict[str, Any]]:
    """Fetch products (semantic or text) and apply ranking or product_mix."""
    fetch_limit = limit
    product_mix = None
    cdc = await get_composite_discovery_config()
    if cdc and cdc.get("product_mix"):
        mix = cdc.get("product_mix")
        if isinstance(mix, list) and len(mix) > 0:
            product_mix = mix
            fetch_limit = max(limit, 50)

    admin = await get_admin_orchestration_settings()
    use_aggregator = True  # DiscoveryAggregator is default; timeout from admin or 5000ms

    if not query or not query.strip():
        if use_aggregator:
            products = await _fetch_via_aggregator("", fetch_limit, partner_id, exclude_partner_id, experience_tag, experience_tags)
        else:
            products = await search_products(query="", limit=fetch_limit, partner_id=partner_id, exclude_partner_id=exclude_partner_id, experience_tag=experience_tag, experience_tags=experience_tags)
    elif is_browse_query(query):
        if use_aggregator:
            products = await _fetch_via_aggregator("", fetch_limit, partner_id, exclude_partner_id, experience_tag, experience_tags)
        else:
            products = await search_products(query="", limit=fetch_limit, partner_id=partner_id, exclude_partner_id=exclude_partner_id, experience_tag=experience_tag, experience_tags=experience_tags)
    else:
        # Try semantic search first when embedding is configured (then fall back to aggregator/text)
        products = []
        if use_semantic and getattr(settings, "embedding_configured", False):
            products = await semantic_search(
                query=query,
                limit=fetch_limit,
                partner_id=partner_id,
                exclude_partner_id=exclude_partner_id,
                experience_tag=experience_tag,
                experience_tags=experience_tags,
            )
        if not products:
            if use_aggregator:
                products = await _fetch_via_aggregator(query, fetch_limit, partner_id, exclude_partner_id, experience_tag, experience_tags)
            else:
                products = await search_products(
                    query=query,
                    limit=fetch_limit,
                    partner_id=partner_id,
                    exclude_partner_id=exclude_partner_id,
                    experience_tag=experience_tag,
                    experience_tags=experience_tags,
                )
        if not products and query.lower() in ("gifts", "gift"):
            for fallback in ("gift", "birthday", "present"):
                if fallback != query.lower():
                    if use_aggregator:
                        products = await _fetch_via_aggregator(fallback, fetch_limit, partner_id, exclude_partner_id, experience_tag, experience_tags)
                    else:
                        products = await search_products(query=fallback, limit=fetch_limit, partner_id=partner_id, exclude_partner_id=exclude_partner_id, experience_tag=experience_tag, experience_tags=experience_tags)
                    if products:
                        break

    if not products:
        return []

    if product_mix:
        product_ids = [str(p.get("id", "")) for p in products if p.get("id")]
        partner_ids = list({str(p.get("partner_id", "")) for p in products if p.get("partner_id")})
        partners_map = await get_partners_by_ids(partner_ids)
        partner_ratings_map = await get_partner_ratings_map(partner_ids)
        active_sponsorships = await get_active_sponsorships(product_ids)
        return await _apply_product_mix(
            products, product_mix, limit,
            partners_map, partner_ratings_map, active_sponsorships,
        )
    # Use first tag for boost when multiple tags provided
    boost_tag = (experience_tags[0] if experience_tags else experience_tag) if (experience_tags or experience_tag) else None
    return await _apply_ranking(products, experience_tag=boost_tag, experience_tag_boost_amount=experience_tag_boost_amount)


async def search(
    query: str,
    limit: int = 20,
    location: Optional[str] = None,
    partner_id: Optional[str] = None,
    exclude_partner_id: Optional[str] = None,
    use_semantic: bool = True,
    experience_tag: Optional[str] = None,
    experience_tags: Optional[List[str]] = None,
    experience_tag_boost_amount: float = 0.2,
) -> List[Dict[str, Any]]:
    """
    Unified product discovery: semantic search when available, else text search.

    - use_semantic=True: Try pgvector first; fallback to text if no results or embeddings unavailable
    - location: Reserved for future geospatial filter (PostGIS)
    - experience_tag: Optional filter/boost by experience tag (e.g. baby, celebration)
    - experience_tags: Optional filter by multiple tags (AND semantics; e.g. luxury, travel-friendly)
    - experience_tag_boost_amount: Score boost for products matching experience tag (default 0.2)
    - Applies action-word stripping when query looks like full sentence (e.g. "wanna book limo" -> "limo")
    - Applies partner ranking when ranking_enabled in platform_config
    - When composite_discovery_config.product_mix is set: composes results from slices (price, rating, sponsored, etc.)
    """
    if not query or not query.strip():
        return await _fetch_and_rank("", limit, partner_id, exclude_partner_id, use_semantic, experience_tag, experience_tags, experience_tag_boost_amount)

    if is_browse_query(query):
        return await _fetch_and_rank("", limit, partner_id, exclude_partner_id, use_semantic, experience_tag, experience_tags, experience_tag_boost_amount)

    if " " in query.strip():
        derived = derive_search_query(query)
        if derived:
            query = derived

    if use_semantic:
        results = await _fetch_and_rank(query, limit, partner_id, exclude_partner_id, True, experience_tag, experience_tags, experience_tag_boost_amount)
        if results:
            return results

    return await _fetch_and_rank(query, limit, partner_id, exclude_partner_id, False, experience_tag, experience_tags, experience_tag_boost_amount)
