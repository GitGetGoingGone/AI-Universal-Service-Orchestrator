"""Cache partner manifest files in Supabase (Module 1)."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from config import settings
from db import get_supabase


DEFAULT_TTL_SECONDS = 3600


async def fetch_manifest(url: str) -> Optional[Dict[str, Any]]:
    """
    Fetch manifest from URL with conditional request (etag, last-modified).
    Returns parsed JSON or None.
    """
    client = get_supabase()
    if not client:
        return None

    # Check cache
    cache_row = (
        client.table("manifest_cache")
        .select("etag, last_modified, cached_at, cache_ttl")
        .eq("manifest_url", url)
        .maybe_single()
        .execute()
    )
    headers = {}
    if cache_row.data:
        # Prefer etag for conditional request
        if cache_row.data.get("etag"):
            headers["If-None-Match"] = cache_row.data["etag"]
        elif cache_row.data.get("last_modified"):
            headers["If-Modified-Since"] = cache_row.data["last_modified"]

    try:
        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.get(url, headers=headers or None)
            if resp.status_code == 304:
                # Use cached data from partner_manifests
                return _get_cached_manifest_data(client, url)
            if resp.status_code != 200:
                return None

            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None
            if data is None:
                # Try JSONL (one JSON per line)
                try:
                    lines = resp.text.strip().split("\n")
                    data = [json.loads(ln) for ln in lines if ln]
                except Exception:
                    return None

            # Update cache metadata
            etag = resp.headers.get("etag")
            last_modified = resp.headers.get("last-modified")
            client.table("manifest_cache").upsert(
                {
                    "manifest_url": url,
                    "etag": etag,
                    "last_modified": last_modified,
                    "cached_at": datetime.utcnow().isoformat(),
                    "hit_count": (cache_row.data.get("hit_count") or 0) + 1 if cache_row.data else 1,
                    "last_hit_at": datetime.utcnow().isoformat(),
                },
                on_conflict="manifest_url",
            ).execute()

            return data
    except Exception:
        return None


def _get_cached_manifest_data(client, url: str) -> Optional[Dict[str, Any]]:
    """Get cached manifest_data from partner_manifests (expires_at in future)."""
    row = (
        client.table("partner_manifests")
        .select("manifest_data")
        .eq("manifest_url", url)
        .gt("expires_at", datetime.utcnow().isoformat())
        .eq("validation_status", "valid")
        .maybe_single()
        .execute()
    )
    return row.data.get("manifest_data") if row.data else None


async def cache_partner_manifest(
    partner_id: str,
    manifest_url: str,
    manifest_type: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> Optional[Dict[str, Any]]:
    """
    Fetch manifest, parse via adapter, cache in partner_manifests.
    manifest_type: 'ucp' | 'acp'
    Returns parsed products list or None.
    """
    data = await fetch_manifest(manifest_url)
    if not data:
        return None

    from protocols.acp_adapter import parse_acp_feed
    from protocols.ucp_adapter import parse_ucp_feed

    if manifest_type.lower() == "acp":
        products = parse_acp_feed(data)
    elif manifest_type.lower() == "ucp":
        products = parse_ucp_feed(data)
    else:
        products = data if isinstance(data, list) else [data]

    client = get_supabase()
    if not client:
        return products

    expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
    payload = {
        "partner_id": partner_id,
        "manifest_url": manifest_url,
        "manifest_type": manifest_type,
        "manifest_data": {"products": products, "cached_at": datetime.utcnow().isoformat()},
        "expires_at": expires_at,
        "last_validated_at": datetime.utcnow().isoformat(),
        "validation_status": "valid",
    }

    # Update existing or insert
    existing = (
        client.table("partner_manifests")
        .select("id")
        .eq("partner_id", partner_id)
        .eq("manifest_url", manifest_url)
        .execute()
    )
    if existing.data:
        client.table("partner_manifests").update(payload).eq("id", existing.data[0]["id"]).execute()
    else:
        client.table("partner_manifests").insert(payload).execute()

    return products
