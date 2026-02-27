"""
Protocol-Aware Discovery Aggregator.

Fans out to LocalDB, UCP Manifest, and MCP drivers with strict timeout handling.
Normalizes all responses into UCPProduct schema (capabilities, features) to prevent LLM hallucination.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from .discovery import is_browse_query

logger = logging.getLogger(__name__)


@dataclass
class UCPProduct:
    """Normalized product schema with explicit capabilities and features to prevent LLM hallucination."""

    id: str
    name: str
    description: str = ""
    price: float = 0.0
    currency: str = "USD"
    partner_id: Optional[str] = None
    source: str = "DB"  # DB | UCP | MCP
    capabilities: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    url: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_eligible_search: bool = True
    is_eligible_checkout: bool = False
    sold_count: int = 0
    experience_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API/LLM context."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "currency": self.currency,
            "partner_id": self.partner_id,
            "source": self.source,
            "capabilities": list(self.capabilities),
            "features": list(self.features),
            "url": self.url,
            "brand": self.brand,
            "image_url": self.image_url,
            "metadata": self.metadata,
            "is_eligible_search": self.is_eligible_search,
            "is_eligible_checkout": self.is_eligible_checkout,
            "sold_count": self.sold_count,
            "experience_tags": list(self.experience_tags),
        }


def _normalize_to_ucp_product(raw: Dict[str, Any], source: str = "DB") -> UCPProduct:
    """Normalize raw product dict to UCPProduct with explicit capabilities/features."""
    caps = raw.get("capabilities")
    if isinstance(caps, str):
        caps = [c.strip() for c in caps.split(",") if c.strip()]
    elif isinstance(caps, list):
        caps = [str(c) for c in caps if c]
    else:
        caps = []

    feats = raw.get("features")
    if isinstance(feats, str):
        feats = [f.strip() for f in feats.split(",") if f.strip()]
    elif isinstance(feats, list):
        feats = [str(f) for f in feats if f]
    else:
        feats = []
    exp_tags = raw.get("experience_tags")
    if isinstance(exp_tags, list):
        exp_tags = [str(t).strip().lower() for t in exp_tags if t and str(t).strip()]
    else:
        exp_tags = []
    meta = raw.get("metadata") or {}
    if isinstance(meta, dict):
        pass
    else:
        meta = {}

    return UCPProduct(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", raw.get("title", ""))),
        description=str(raw.get("description", "")),
        price=float(raw.get("price", raw.get("offers", {}).get("price", 0) if isinstance(raw.get("offers"), dict) else 0)),
        currency=str(raw.get("currency", raw.get("offers", {}).get("priceCurrency", "USD") if isinstance(raw.get("offers"), dict) else "USD")),
        partner_id=str(raw["partner_id"]) if raw.get("partner_id") else None,
        source=source,
        capabilities=caps,
        features=feats,
        url=raw.get("url"),
        brand=raw.get("brand"),
        image_url=raw.get("image_url"),
        metadata=meta,
        is_eligible_search=bool(raw.get("is_eligible_search", True)),
        is_eligible_checkout=bool(raw.get("is_eligible_checkout", False)),
        sold_count=int(raw.get("sold_count", 0)),
        experience_tags=exp_tags,
    )


class LocalDBDriver:
    """Driver that calls the local DB search (search_products)."""

    def __init__(self, search_fn: Callable[..., Awaitable[List[Dict[str, Any]]]]):
        self._search = search_fn

    async def search(
        self,
        query: str,
        limit: int = 20,
        partner_id: Optional[str] = None,
        exclude_partner_id: Optional[str] = None,
        experience_tag: Optional[str] = None,
        experience_tags: Optional[List[str]] = None,
    ) -> List[UCPProduct]:
        try:
            raw = await self._search(
                query=query,
                limit=limit,
                partner_id=partner_id,
                exclude_partner_id=exclude_partner_id,
                experience_tag=experience_tag,
                experience_tags=experience_tags,
            )
            return [_normalize_to_ucp_product(p, "DB") for p in (raw if isinstance(raw, list) else [])]
        except Exception as e:
            logger.warning("LocalDBDriver search failed: %s", e)
            return []


class UCPManifestDriver:
    """Driver that fetches from partner /.well-known/ucp.json (or /.well-known/ucp) and catalog."""

    def __init__(self, get_partner_manifest_urls: Optional[Callable[[], Awaitable[List[str]]]] = None):
        self._get_urls = get_partner_manifest_urls

    async def search(
        self,
        query: str,
        limit: int = 20,
        partner_id: Optional[str] = None,
        exclude_partner_id: Optional[str] = None,
    ) -> List[UCPProduct]:
        if not self._get_urls:
            return []
        try:
            import httpx
            urls = await self._get_urls()
            if not urls:
                return []
            all_items: List[UCPProduct] = []
            headers = {"Accept": "application/json", "User-Agent": "USO-Orchestrator/1.0 (UCP Discovery)"}
            for base_url in urls[:5]:
                try:
                    manifest_url = f"{base_url.rstrip('/')}/.well-known/ucp.json"
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        r = await client.get(manifest_url, headers=headers)
                        if r.status_code != 200:
                            manifest_url = f"{base_url.rstrip('/')}/.well-known/ucp"
                            r = await client.get(manifest_url, headers=headers)
                        if r.status_code != 200:
                            continue
                        data = r.json()
                    catalog_url = None
                    ucp = data.get("ucp", data)
                    if isinstance(ucp, dict):
                        services = ucp.get("services", {})
                        if isinstance(services, dict):
                            dev = services.get("dev.ucp.shopping", services)
                            if isinstance(dev, dict):
                                rest = dev.get("rest", dev)
                                if isinstance(rest, dict):
                                    catalog_url = rest.get("endpoint", rest.get("catalog"))
                    base = base_url.rstrip("/")
                    if not catalog_url:
                        catalog_base = f"{base}/api/v1/ucp"
                    else:
                        cu = catalog_url.rstrip("/")
                        for suffix in ("/items", "/search", "/item", "/products"):
                            if cu.endswith(suffix):
                                catalog_base = cu[: -len(suffix)]
                                break
                        else:
                            catalog_base = cu
                    # Try primary path /items, then fallbacks: /search, /item, /products
                    catalog_paths = ["/items", "/search", "/item", "/products"]
                    cat = None
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        for path in catalog_paths:
                            url = f"{catalog_base.rstrip('/')}{path}"
                            r = await client.get(url, params={"q": query, "limit": limit}, headers=headers)
                            if r.status_code == 200:
                                try:
                                    cat = r.json()
                                    break
                                except Exception:
                                    pass
                    if not cat:
                        continue
                    items = cat.get("items", cat.get("products", []))
                    if not items and isinstance(cat.get("item"), dict):
                        items = [cat["item"]]
                    for it in (items or [])[:limit]:
                        raw = it if isinstance(it, dict) else {}
                        pid = raw.get("id", raw.get("item", {}).get("id", ""))
                        if isinstance(pid, dict):
                            pid = pid.get("id", "")
                        p = _normalize_to_ucp_product(
                            {
                                "id": pid,
                                "name": raw.get("title", raw.get("name", "")),
                                "description": raw.get("description", ""),
                                "price": raw.get("price", 0) / 100.0 if isinstance(raw.get("price"), (int, float)) else 0,
                                "currency": raw.get("currency", "USD"),
                                "image_url": raw.get("image_url"),
                                "capabilities": raw.get("capabilities", []),
                                "features": raw.get("features", []),
                            },
                            "UCP",
                        )
                        all_items.append(p)
                except Exception as e:
                    logger.debug("UCP manifest %s failed: %s", base_url, e)
            return all_items[:limit]
        except Exception as e:
            logger.warning("UCPManifestDriver search failed: %s", e)
            return []


class MCPDriver:
    """Driver that fetches from MCP (Model Context Protocol) tools. Placeholder until MCP client wired."""

    def __init__(self, mcp_search_fn: Optional[Callable[..., Awaitable[List[Dict[str, Any]]]]] = None):
        self._mcp_search = mcp_search_fn

    async def search(
        self,
        query: str,
        limit: int = 20,
        partner_id: Optional[str] = None,
        exclude_partner_id: Optional[str] = None,
    ) -> List[UCPProduct]:
        if not self._mcp_search:
            return []
        try:
            raw = await self._mcp_search(query=query, limit=limit)
            return [_normalize_to_ucp_product(p, "MCP") for p in (raw if isinstance(raw, list) else [])]
        except Exception as e:
            logger.warning("MCPDriver search failed: %s", e)
            return []


class DiscoveryAggregator:
    """
    Async aggregator that fans out to LocalDB, UCP, MCP with strict timeout.
    Merges and dedupes by product id; returns list of UCPProduct.
    """

    def __init__(
        self,
        local_db_driver: Optional[LocalDBDriver] = None,
        ucp_driver: Optional[UCPManifestDriver] = None,
        mcp_driver: Optional[MCPDriver] = None,
        timeout_ms: int = 5000,
    ):
        self._local = local_db_driver
        self._ucp = ucp_driver
        self._mcp = mcp_driver
        self._timeout_ms = max(500, min(60000, timeout_ms))

    async def search(
        self,
        query: str,
        limit: int = 20,
        partner_id: Optional[str] = None,
        exclude_partner_id: Optional[str] = None,
        experience_tag: Optional[str] = None,
        experience_tags: Optional[List[str]] = None,
    ) -> List[UCPProduct]:
        if is_browse_query(query):
            query = ""
        timeout_sec = self._timeout_ms / 1000.0
        tasks: List[asyncio.Task] = []
        if self._local:
            tasks.append(
                asyncio.create_task(
                    self._local.search(
                        query=query,
                        limit=limit,
                        partner_id=partner_id,
                        exclude_partner_id=exclude_partner_id,
                        experience_tag=experience_tag,
                        experience_tags=experience_tags,
                    )
                )
            )
        if self._ucp:
            tasks.append(
                asyncio.create_task(
                    self._ucp.search(query=query, limit=limit, partner_id=partner_id, exclude_partner_id=exclude_partner_id)
                )
            )
        if self._mcp:
            tasks.append(
                asyncio.create_task(
                    self._mcp.search(query=query, limit=limit, partner_id=partner_id, exclude_partner_id=exclude_partner_id)
                )
            )
        if not tasks:
            return []
        try:
            raw_results: List[Union[List[UCPProduct], BaseException]] = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            logger.warning("DiscoveryAggregator timed out after %sms", self._timeout_ms)
            return []
        merged: Dict[str, UCPProduct] = {}
        for r in raw_results:
            if isinstance(r, Exception):
                logger.warning("Discovery driver failed: %s", r)
                continue
            for p in r if isinstance(r, list) else []:
                if isinstance(p, UCPProduct) and p.id:
                    merged[p.id] = p
        out = list(merged.values())[:limit]
        return out
