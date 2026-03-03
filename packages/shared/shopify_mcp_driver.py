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
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

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

    Known shape (Kylie/Shopify search_shop_catalog):
    - Top level: result.content[].text (JSON-RPC) or content[].text (Playground).
    - Parsed text: { "products": [ { "product_id", "title", "description", "url", "image_url", "price_range": { "min", "max", "currency" }, ... } ], "pagination", "available_filters", "instructions" }.
    - Each product uses product_id (not id), title (not name), and price_range with string min/max.

    Also handles: result wrapper, data.data.products, top-level products/items, and JSON-RPC error.
    """
    out: List[Dict[str, Any]] = []
    if not data or not isinstance(data, dict):
        return out

    # JSON-RPC error: log and return empty (use debug for auth failures to reduce noise)
    err = data.get("error")
    if isinstance(err, dict):
        msg = err.get("message", err.get("data", ""))
        code = err.get("code")
        if code == -32000 and "auth" in str(msg).lower():
            logger.debug("Shopify MCP auth error (partner may require token or be UCP-only): code=%s message=%s", code, msg)
        else:
            logger.warning(
                "Shopify MCP JSON-RPC error: code=%s message=%s",
                code,
                msg,
            )
        return out

    # content[] with type/text (known shape: content[0].text is JSON string with "products" key)
    content = data.get("content")
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and "text" in c:
                try:
                    parsed = json.loads(c["text"])
                    if isinstance(parsed, dict) and "products" in parsed:
                        for p in parsed.get("products") or []:
                            if isinstance(p, dict):
                                out.append(_map_shopify_product(p, slug, price_premium))
                        if out:
                            return out
                    out.extend(_extract_products_from_mcp_response(parsed, slug, price_premium))
                except (json.JSONDecodeError, TypeError):
                    pass
            elif isinstance(c, dict) and ("products" in c or "items" in c):
                lst = c.get("products") or c.get("items") or []
                for p in lst:
                    if isinstance(p, dict):
                        out.append(_map_shopify_product(p, slug, price_premium))
        if out:
            return out

    # Direct products/items at top level (do NOT use data.content here; it's blocks, not product list)
    items = data.get("products") or data.get("items")
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

    # data.data.products (some APIs nest under data)
    inner = data.get("data")
    if isinstance(inner, dict):
        inner_items = inner.get("products") or inner.get("items")
        if isinstance(inner_items, list):
            for p in inner_items:
                if isinstance(p, dict):
                    out.append(_map_shopify_product(p, slug, price_premium))
            return out

    # JSON-RPC result wrapper
    result = data.get("result")
    if isinstance(result, dict):
        return _extract_products_from_mcp_response(result, slug, price_premium)
    if isinstance(result, list):
        for r in result:
            if isinstance(r, dict):
                if r.get("products") is not None or r.get("content") is not None or r.get("result") is not None:
                    out.extend(_extract_products_from_mcp_response(r, slug, price_premium))
                else:
                    out.append(_map_shopify_product(r, slug, price_premium))
        return out

    return out


def _map_shopify_product(raw: Dict[str, Any], slug: str, price_premium: float) -> Dict[str, Any]:
    """Map Shopify product/variant to normalized dict for UCPProduct."""
    # Shopify product shape: id, title, body_html, variants: [{id, price, ...}], images: [{src}]
    # Also: product_id, title, description, image_url, price_range: {min, max, currency} (Storefront API / MCP)
    pid = str(raw.get("id", raw.get("variant_id", raw.get("product_id", ""))))
    if pid and not str(pid).startswith("gid:"):
        ext_id = f"shopify_{slug}_{pid}"
    else:
        ext_id = pid or f"shopify_{slug}_unknown"

    title = str(raw.get("title", raw.get("name", "")))
    description = str(raw.get("body_html", raw.get("description", "")))
    if description and len(description) > 2000:
        description = description[:2000] + "..."

    # Price: variants[0].price, top-level price, or price_range.min/max (Storefront/MCP shape)
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
        pr = raw.get("price_range")
        if isinstance(pr, dict):
            for k in ("min", "max"):
                v = pr.get(k)
                if v is not None:
                    try:
                        price_val = float(v)
                        break
                    except (TypeError, ValueError):
                        pass
    if price_val is None:
        price_val = 0.0

    # Apply premium
    if price_premium and price_premium > 0:
        price_val = price_val * (1 + price_premium / 100.0)

    # Currency: price_range.currency or top-level
    currency = "USD"
    if isinstance(raw.get("price_range"), dict) and raw["price_range"].get("currency"):
        currency = str(raw["price_range"]["currency"])
    elif raw.get("currency"):
        currency = str(raw.get("currency", "USD"))

    # Image: image_url (MCP/Storefront), images[0].src, or image
    images = raw.get("images", [])
    image_url = raw.get("image_url")
    if not image_url and images and isinstance(images, list) and len(images) > 0:
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
        "currency": currency,
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
                try:
                    async with httpx.AsyncClient(timeout=self._timeout) as client:
                        r = await client.post(mcp_url, json=payload, headers=headers)
                except Exception as e:
                    logger.warning("Shopify MCP request failed %s: %s", mcp_url, e)
                    return []
                if r.status_code != 200:
                    logger.warning(
                        "Shopify MCP %s returned %s; body snippet: %s",
                        mcp_url,
                        r.status_code,
                        (r.text or "")[:300],
                    )
                    return []
                try:
                    data = r.json()
                except Exception as e:
                    logger.warning("Shopify MCP %s non-JSON response: %s", mcp_url, (r.text or "")[:200])
                    return []
                products = _extract_products_from_mcp_response(data, slug, premium)
                if not products:
                    err = data.get("error") if isinstance(data, dict) else None
                    err_msg = err.get("message", str(err)) if isinstance(err, dict) else None
                    logger.info(
                        "Shopify MCP %s returned 200 but no products extracted. keys=%s%s",
                        mcp_url,
                        list(data.keys()) if isinstance(data, dict) else type(data).__name__,
                        f" error={err_msg}" if err_msg else "",
                    )
                return products

            results: List[Union[List[Dict[str, Any]], BaseException]] = await asyncio.gather(
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
