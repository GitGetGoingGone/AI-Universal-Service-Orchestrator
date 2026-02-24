"""pgvector-based semantic product search (Module 1)."""

import logging
from typing import Any, Dict, List, Optional

import httpx

from config import settings
from db import get_supabase

logger = logging.getLogger(__name__)

# pgvector schema expects 1536 dimensions (text-embedding-ada-002 / text-embedding-3-small)
EMBEDDING_DIMENSION = 1536


async def get_query_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for search query via OpenAI or Azure OpenAI.
    Returns None when not configured or on API error.
    """
    if not text or not text.strip():
        return None
    if not getattr(settings, "embedding_configured", False):
        return None

    provider = getattr(settings, "embedding_provider", "azure") or "azure"
    model = getattr(settings, "embedding_model", "text-embedding-3-small") or "text-embedding-3-small"

    try:
        if provider == "openai":
            api_key = getattr(settings, "openai_api_key", "") or ""
            if not api_key:
                return None
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "input": text.strip()[:8192]},
                )
                r.raise_for_status()
                data = r.json()
        else:
            endpoint = getattr(settings, "azure_openai_endpoint", "") or ""
            api_key = getattr(settings, "azure_openai_api_key", "") or ""
            if not endpoint or not api_key:
                return None
            url = f"{endpoint}/openai/deployments/{model}/embeddings?api-version=2024-02-15-preview"
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    url,
                    headers={"api-key": api_key, "Content-Type": "application/json"},
                    json={"input": text.strip()[:8192]},
                )
                r.raise_for_status()
                data = r.json()

        items = data.get("data") if isinstance(data, dict) else None
        if not items or not isinstance(items, list):
            return None
        emb = items[0].get("embedding") if isinstance(items[0], dict) else None
        if not emb or not isinstance(emb, list):
            return None
        vec = [float(x) for x in emb]
        if len(vec) < EMBEDDING_DIMENSION:
            logger.warning("Embedding dimension %s < %s; check model", len(vec), EMBEDDING_DIMENSION)
            return None
        return vec[:EMBEDDING_DIMENSION]
    except Exception as e:
        logger.warning("Embedding API failed: %s", e)
        return None


def _get_product_embedding_input(product: Dict[str, Any]) -> str:
    """Build text for product embedding from name, description, description_kb, capabilities."""
    parts = [
        product.get("name") or "",
        product.get("description") or "",
        product.get("description_kb") or "",
    ]
    caps = product.get("capabilities")
    if isinstance(caps, list):
        parts.extend(str(c) for c in caps)
    elif isinstance(caps, dict):
        parts.extend(f"{k}: {v}" for k, v in caps.items())
    return " ".join(p for p in parts if p).strip()


def _get_kb_article_embedding_input(article: Dict[str, Any]) -> str:
    """Build text for KB article embedding from title and content."""
    title = (article.get("title") or "").strip()
    content = (article.get("content") or "").strip()
    return f"{title} {content}".strip()


async def backfill_kb_article_embedding(article_id: str) -> bool:
    """
    Generate and store embedding for a partner KB article if missing.
    Returns True if embedding was stored.
    """
    client = get_supabase()
    if not client:
        return False

    try:
        result = (
            client.table("partner_kb_articles")
            .select("id, title, content")
            .eq("id", article_id)
            .eq("is_active", True)
            .single()
            .execute()
        )
        row = result.data if isinstance(result.data, dict) else (result.data[0] if result.data and isinstance(result.data, list) else None)
    except Exception:
        return False
    if not row or not isinstance(row, dict):
        return False

    inp = _get_kb_article_embedding_input(row)
    if not inp:
        return False

    embedding = await get_query_embedding(inp)
    if not embedding:
        return False

    try:
        client.table("partner_kb_articles").update({"embedding": embedding}).eq("id", article_id).execute()
        return True
    except Exception:
        return False


async def backfill_all_kb_article_embeddings(limit: int = 500) -> Dict[str, Any]:
    """
    Backfill embeddings for partner KB articles that have no embedding yet.
    Returns dict with updated_count, failed_count, total_processed.
    """
    client = get_supabase()
    if not client:
        return {"updated_count": 0, "failed_count": 0, "total_processed": 0, "error": "no_db"}

    try:
        result = (
            client.table("partner_kb_articles")
            .select("id")
            .eq("is_active", True)
            .is_("embedding", "null")
            .limit(limit)
            .execute()
        )
        rows = result.data or []
    except Exception as e:
        logger.warning("Failed to fetch KB articles for backfill: %s", e)
        return {"updated_count": 0, "failed_count": 0, "total_processed": 0, "error": str(e)}

    updated = 0
    failed = 0
    for row in rows:
        aid = row.get("id") if isinstance(row, dict) else None
        if not aid:
            continue
        ok = await backfill_kb_article_embedding(str(aid))
        if ok:
            updated += 1
        else:
            failed += 1

    return {
        "updated_count": updated,
        "failed_count": failed,
        "total_processed": len(rows),
    }


async def semantic_search_kb_articles(
    query: str,
    limit: int = 20,
    partner_id: Optional[str] = None,
    exclude_partner_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search partner KB articles by semantic similarity (pgvector).
    Returns list of dicts with id, partner_id, title, content, sort_order, created_at.
    Falls back to empty list if embeddings not configured or query embedding fails.
    """
    client = get_supabase()
    if not client:
        return []

    embedding = await get_query_embedding(query)
    if not embedding:
        return []

    try:
        embedding_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"
        kwargs: Dict[str, Any] = {
            "query_embedding": embedding_str,
            "match_count": limit,
            "match_threshold": 0.0,
        }
        if partner_id:
            kwargs["filter_partner_id"] = partner_id
        if exclude_partner_id:
            kwargs["exclude_partner_id"] = exclude_partner_id

        result = client.rpc("match_kb_articles", kwargs).execute()
        rows = result.data or []

        out = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            out.append({
                "id": r.get("id"),
                "partner_id": r.get("partner_id"),
                "title": r.get("title"),
                "content": r.get("content"),
                "sort_order": r.get("sort_order"),
                "created_at": r.get("created_at"),
            })
        return out[:limit]
    except Exception as e:
        logger.warning("KB articles semantic search failed: %s", e)
        return []


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
        .select("id, name, description, description_kb, capabilities")
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


async def backfill_all_product_embeddings(limit: int = 500) -> Dict[str, Any]:
    """
    Backfill embeddings for all products that have no embedding yet.
    Returns dict with updated_count, failed_count, skipped_count, total_processed.
    """
    client = get_supabase()
    if not client:
        return {"updated_count": 0, "failed_count": 0, "skipped_count": 0, "total_processed": 0, "error": "no_db"}

    try:
        result = (
            client.table("products")
            .select("id")
            .is_("deleted_at", "null")
            .is_("embedding", "null")
            .limit(limit)
            .execute()
        )
        rows = result.data or []
    except Exception as e:
        logger.warning("Failed to fetch products for backfill: %s", e)
        return {"updated_count": 0, "failed_count": 0, "skipped_count": 0, "total_processed": 0, "error": str(e)}

    updated = 0
    failed = 0
    for row in rows:
        pid = row.get("id") if isinstance(row, dict) else None
        if not pid:
            continue
        ok = await backfill_product_embedding(str(pid))
        if ok:
            updated += 1
        else:
            failed += 1

    return {
        "updated_count": updated,
        "failed_count": failed,
        "skipped_count": 0,
        "total_processed": len(rows),
    }


async def semantic_search(
    query: str,
    limit: int = 20,
    partner_id: Optional[str] = None,
    exclude_partner_id: Optional[str] = None,
    experience_tag: Optional[str] = None,
    experience_tags: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Search products by semantic similarity (pgvector).
    Falls back to empty list if embeddings not configured or query embedding fails.
    When experience_tags (list) is set, only products that contain ALL tags are returned (AND semantics).
    """
    client = get_supabase()
    if not client:
        return []

    embedding = await get_query_embedding(query)
    if not embedding:
        return []

    tags_list: List[str] = []
    if experience_tags:
        tags_list = [str(t).strip().lower() for t in experience_tags if t and str(t).strip()]
    if not tags_list and experience_tag and experience_tag.strip():
        tags_list = [experience_tag.strip().lower()]

    try:
        # pgvector expects string format for RPC: "[0.1,0.2,...]"
        embedding_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"

        kwargs = {
            "query_embedding": embedding_str,
            "match_count": limit * 3 if tags_list else limit,  # fetch extra for post-filter when multi-tag
            "match_threshold": 0.0,
        }
        if partner_id:
            kwargs["filter_partner_id"] = partner_id
        if exclude_partner_id:
            kwargs["exclude_partner_id"] = exclude_partner_id
        if tags_list:
            kwargs["filter_experience_tag"] = tags_list[0]

        result = client.rpc("match_products_v2", kwargs).execute()
        rows = result.data or []

        # Normalize to dict with expected keys (created_at for ranking, sold_count for product_mix, experience_tags for discovery)
        select_cols = ("id", "name", "description", "price", "currency", "capabilities", "metadata", "partner_id", "created_at", "sold_count", "experience_tags")
        out = [
            {k: r.get(k) for k in select_cols if k in r}
            for r in rows
        ]
        # AND semantics: keep only products that have all requested tags
        if len(tags_list) > 1:
            out = [
                r for r in out
                if r and isinstance(r.get("experience_tags"), list)
                and set(str(t).strip().lower() for t in r["experience_tags"] if t) >= set(tags_list)
            ]
        return out[:limit]
    except Exception:
        return []
