"""pgvector-based semantic product search (Module 1)."""

from typing import Any, Dict, List, Optional

from config import settings
from db import get_supabase


_embedding_client: Optional[Any] = None


def _get_embedding_client():
    """Lazy Azure OpenAI client for embeddings."""
    global _embedding_client
    if _embedding_client is not None:
        return _embedding_client
    if not settings.embedding_configured:
        return None
    try:
        from openai import AzureOpenAI

        _embedding_client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version="2024-02-01",
            azure_endpoint=settings.azure_openai_endpoint.rstrip("/"),
        )
        return _embedding_client
    except Exception:
        return None


async def get_query_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for search query.
    Uses Azure OpenAI text-embedding-ada-002 or text-embedding-3-small (1536 dims).
    """
    import asyncio

    client = _get_embedding_client()
    if not client or not text or not text.strip():
        return None

    try:
        response = await asyncio.to_thread(
            lambda: client.embeddings.create(
                input=text.strip()[:8000],
                model=settings.embedding_deployment,
            )
        )
        if response.data and len(response.data) > 0:
            return response.data[0].embedding
    except Exception:
        pass
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

        # Normalize to dict with expected keys
        select_cols = ("id", "name", "description", "price", "currency", "capabilities", "metadata", "partner_id")
        return [
            {k: r.get(k) for k in select_cols if k in r}
            for r in rows
        ]
    except Exception:
        return []
