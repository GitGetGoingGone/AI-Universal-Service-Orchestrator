"""pgvector-based semantic product search (Module 1)."""

from typing import Any, Dict, List, Optional

from db import get_supabase


async def get_query_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for search query.
    Embedding config is in Platform Config (llm_providers). Returns None when not configured.
    """
    return None


def _get_product_embedding_input(product: Dict[str, Any]) -> str:
    """Build text for product embedding from name, description, capabilities."""
    parts = [
        product.get("name") or "",
        product.get("description") or "",
    ]
    caps = product.get("capabilities")
    if isinstance(caps, list):
        parts.extend(str(c) for c in caps)
    elif isinstance(caps, dict):
        parts.extend(f"{k}: {v}" for k, v in caps.items())
    return " ".join(p for p in parts if p).strip()


async def backfill_product_embedding(product_id: str) -> bool:
    """
    Generate and store embedding for a product if missing.
    Returns True if embedding was stored.
    """
    import asyncio

    client = get_supabase()
    if not client:
        return False

    product = (
        client.table("products")
        .select("id, name, description, capabilities")
        .eq("id", product_id)
        .is_("deleted_at", "null")
        .single()
        .execute()
    )
    if not product.data:
        return False

    inp = _get_product_embedding_input(product.data)
    if not inp:
        return False

    embedding = await get_query_embedding(inp)
    if not embedding:
        return False

    try:
        client.table("products").update({"embedding": embedding}).eq("id", product_id).execute()
        return True
    except Exception:
        return False


async def semantic_search(
    query: str,
    limit: int = 20,
    partner_id: Optional[str] = None,
    exclude_partner_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search products by semantic similarity (pgvector).
    Falls back to empty list if embeddings not configured or query embedding fails.
    """
    client = get_supabase()
    if not client:
        return []

    embedding = await get_query_embedding(query)
    if not embedding:
        return []

    try:
        # pgvector expects string format for RPC: "[0.1,0.2,...]"
        embedding_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"

        kwargs = {
            "query_embedding": embedding_str,
            "match_count": limit,
            "match_threshold": 0.0,
        }
        if partner_id:
            kwargs["filter_partner_id"] = partner_id
        if exclude_partner_id:
            kwargs["exclude_partner_id"] = exclude_partner_id

        result = client.rpc("match_products", kwargs).execute()
        rows = result.data or []

        # Normalize to dict with expected keys (created_at for ranking, sold_count for product_mix)
        select_cols = ("id", "name", "description", "price", "currency", "capabilities", "metadata", "partner_id", "created_at", "sold_count")
        return [
            {k: r.get(k) for k in select_cols if k in r}
            for r in rows
        ]
    except Exception:
        return []
