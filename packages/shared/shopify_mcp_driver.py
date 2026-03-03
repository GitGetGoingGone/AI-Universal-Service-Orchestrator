"""
Shopify Storefront MCP Driver.

Calls Shopify stores' public /api/mcp endpoint (search_shop_catalog tool).
Maps responses to UCPProduct with optional price_premium_percent.
Timeout: 3 seconds per request (configurable).
"""

import asyncio
import json
import logging
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default timeout per Shopify MCP request (plan: 3s SLA)
SHOPIFY_MCP_TIMEOUT = 3.0


def _slug_from_shop_url(shop_url: str) -> str:
    """Derive slug from shop_url (e.g. mikesbikes.com -> mikesbikes_com)."""
    s = str(shop_url).strip().lower().replace(".", "_")
    s = re.sub(r"[^a-z0-9_]+", "", s)
    return (s or "shopify")[:64]


def _extract_products_from_mcp_response(data: Any, slug: str, price_premium: float) -> List[Dict[str, Any]]:
    """
    Extract product list from MCP tools/call response.
    Handles: result.content[].text (JSON), result.content[].products, result.products, etc.
    """
    out: List[Dict[str, Any]] = []
    if not data or not isinstance(data, dict):
        return out

    # Direct products/items
    items = data.get("products") or data.get("items") or data.get("content")
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict):
                out.append(_map_shopify_product(it, slug, price_premium))
            elif isinstance(it, str):
                try:
                    parsed = json.loads(it)
                    if isinstance(parsed, list):
                        for p in parsed:
                            if isinstance(p, dict):
                                out.append(_map_shopify_product(p, slug, price_premium))
                    elif isinstance(parsed, dict):
                        out.append(_map_shopify_product(parsed, slug, price_premium))
                except json.JSONDecodeError:
                    pass
        return out

    # JSON-RPC result wrapper
    result = data.get("result")
    if isinstance(result, dict):
        return _extract_products_from_mcp_response(result, slug, price_premium)
    if isinstance(result, list):
        for r in result:
            if isinstance(r, dict):
                out.extend(_extract_products_from_mcp_response(r, slug, price_premium))
        return out

    # content array with text
    content = data.get("content")
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and "text" in c:
                try:
                    parsed = json.loads(c["text"])
                    out.extend(_extract_products_from_mcp_response(parsed, slug, price_premium))
                except (json.JSONDecodeError, TypeError):
                    pass
            elif isinstance(c, dict) and ("products" in c or "items" in c):
                lst = c.get("products") or c.get("items") or []
                for p in lst:
                    if isinstance(p, dict):
                        out.append(_map_shopify_product(p, slug, price_premium))
        return out

    return out


def _map_shopify_product(raw: Dict[str, Any], slug: str, price_premium: float) -> Dict[str, Any]:
    """Map Shopify product/variant to normalized dict for UCPProduct."""
    # Shopify product shape: id, title, body_html, variants: [{id, price, ...}], images: [{src}]
    pid = str(raw.get("id", raw.get("variant_id", raw.get("product_id", ""))))
    if pid and not str(pid).startswith("gid:"):
        ext_id = f"shopify_{slug}_{pid}"
    else:
        ext_id = pid or f"shopify_{slug}_unknown"

    title = str(raw.get("title", raw.get("name", "")))
    description = str(raw.get("body_html", raw.get("description", "")))
    if description and len(description) > 2000:
        description = description[:2000] + "..."

    # Price: variants[0].price or top-level price
    price_val = None
    variants = raw.get("variants", [])
    if variants and isinstance(variants, list) and len(variants) > 0:
        v = variants[0] if isinstance(variants[0], dict) else {}
        p = v.get("price") if isinstance(v, dict) else None
        if p is not None:
            try:
                price_val = float(p)
            except (TypeError, ValueError):
                pass
        if price_val is None and isinstance(v, dict):
            pid = str(v.get("id", pid))
            if pid and not str(pid).startswith("gid:"):
                ext_id = f"shopify_{slug}_{pid}"
    if price_val is None:
        p = raw.get("price")
        if p is not None:
            try:
                price_val = float(p)
            except (TypeError, ValueError):
                pass
    if price_val is None:
        price_val = 0.0

    # Apply premium
    if price_premium and price_premium > 0:
        price_val = price_val * (1 + price_premium / 100.0)

    # Image
    images = raw.get("images", [])
    image_url = None
    if images and isinstance(images, list) and len(images) > 0:
        img = images[0]
        if isinstance(img, dict) and img.get("src"):
            image_url = img["src"]
        elif isinstance(img, str):
            image_url = img
    if not image_url and raw.get("image"):
        img = raw["image"]
        image_url = img.get("src", img) if isinstance(img, dict) else str(img)

    return {
        "id": ext_id,
        "name": title,
        "title": title,
        "description": description,
        "price": price_val,
        "currency": str(raw.get("currency", "USD")),
        "image_url": image_url,
        "partner_id": None,
        "capabilities": [],
        "features": [],
        "metadata": {"source": "SHOPIFY", "slug": slug},
    }


class ShopifyMCPDriver:
    """Driver that calls Shopify Storefront MCP (/api/mcp) search_shop_catalog tool."""

    def __init__(
        self,
        get_shopify_endpoints: Optional[Callable[[], Awaitable[List[Dict[str, Any]]]]] = None,
        timeout: float = SHOPIFY_MCP_TIMEOUT,
    ):
        self._get_endpoints = get_shopify_endpoints
        self._timeout = max(1.0, min(30.0, timeout))

    async def search(
        self,
        query: str,
        limit: int = 20,
        partner_id: Optional[str] = None,
        exclude_partner_id: Optional[str] = None,
    ) -> List[Any]:
        """Search Shopify MCP endpoints; return list of UCPProduct."""
        if not self._get_endpoints:
            return []
        try:
            import httpx
            endpoints = await self._get_endpoints()
            if not endpoints:
                return []

            async def _fetch_one(ep: Dict[str, Any]) -> List[Dict[str, Any]]:
                mcp_url = (ep.get("mcp_endpoint") or "").strip()
                if not mcp_url:
                    return []
                if not mcp_url.startswith("http"):
                    mcp_url = "https://" + mcp_url
                slug = str(ep.get("slug", "") or _slug_from_shop_url(ep.get("shop_url", "")))
                premium = float(ep.get("price_premium_percent") or 0)
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "search_shop_catalog",
                        "arguments": {
                            "query": query or "products",
                            "filters": [{"available": True}],
                        },
                    },
                }
                headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "USO-Orchestrator/1.0 (Shopify MCP)"}
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    r = await client.post(mcp_url, json=payload, headers=headers)
                if r.status_code != 200:
                    logger.debug("Shopify MCP %s returned %s", mcp_url, r.status_code)
                    return []
                try:
                    data = r.json()
                except Exception:
                    return []
                return _extract_products_from_mcp_response(data, slug, premium)

            results: List[List[Dict[str, Any]]] = await asyncio.gather(
                *[_fetch_one(ep) for ep in endpoints[:10]],
                return_exceptions=True,
            )

            from .discovery_aggregator import UCPProduct, _normalize_to_ucp_product

            all_products: List[UCPProduct] = []
            for r in results:
                if isinstance(r, Exception):
                    logger.debug("Shopify MCP driver fetch failed: %s", r)
                    continue
                for raw in (r or [])[:limit]:
                    p = _normalize_to_ucp_product(raw, "SHOPIFY")
                    if p.id:
                        all_products.append(p)

            return all_products[:limit]
        except Exception as e:
            logger.warning("ShopifyMCPDriver search failed: %s", e)
            return []
