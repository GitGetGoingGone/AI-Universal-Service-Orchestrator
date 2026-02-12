"""
Legacy Adapter Layer (Module 2).

Accepts CSV, Excel, or simple JSON feeds; maps to canonical product schema;
normalized products are indexed in the products table for Scout Engine discovery.

Reference: .cursor/plans/03-modules-all.md Module 2, pillars_with_schema_discovery_legacy plan.
"""

import csv
import io
import json
import re
from typing import Any, Dict, List, Optional, Union

# Default column mapping: legacy header -> canonical field
# Supports common exports: Shopify, WooCommerce, generic CSV
DEFAULT_COLUMN_MAP: Dict[str, str] = {
    "handle": "id",
    "id": "id",
    "sku": "id",
    "variant_sku": "id",
    "title": "name",
    "name": "name",
    "product_name": "name",
    "body": "description",
    "body (html)": "description",
    "description": "description",
    "vendor": "brand",
    "brand": "brand",
    "type": "product_type",
    "tags": "tags",
    "variant_price": "price",
    "price": "price",
    "variant_price_value": "price",
    "image_src": "image_url",
    "image_url": "image_url",
    "image": "image_url",
    "url": "url",
    "link": "url",
    "status": "availability",
    "published": "published",
}


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", str(text)).strip()


def _parse_price(val: Any) -> tuple:
    """Parse price from string or number. Returns (price, currency)."""
    if val is None or val == "":
        return 0.0, "USD"
    if isinstance(val, (int, float)):
        return float(val), "USD"
    s = str(val).strip()
    parts = s.replace(",", "").split()
    price = 0.0
    currency = "USD"
    for p in parts:
        try:
            price = float(p)
            break
        except ValueError:
            pass
    if len(parts) >= 2:
        try:
            float(parts[1])
        except ValueError:
            currency = parts[1][:3]
    return price, currency


def _map_row(row: Dict[str, Any], column_map: Dict[str, str]) -> Dict[str, Any]:
    """Map a row dict using column_map (case-insensitive header match)."""
    out: Dict[str, Any] = {}
    row_lower = {k.strip().lower() if k else "": v for k, v in row.items()}
    for legacy_header, canonical_field in column_map.items():
        legacy_lower = legacy_header.lower().strip()
        for k, v in row_lower.items():
            if k == legacy_lower or k.replace(" ", "_") == legacy_lower:
                if v is not None and str(v).strip():
                    out[canonical_field] = str(v).strip()
                break
    return out


def normalize_legacy_product(
    raw: Dict[str, Any],
    column_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Normalize a legacy product row to canonical schema.

    Canonical fields: id, name, description, price, currency, image_url, url, brand,
    availability, capabilities (from tags), metadata.
    """
    cm = column_map or DEFAULT_COLUMN_MAP
    if isinstance(raw, dict) and any(k in raw for k in ("name", "title", "Name", "Title")):
        mapped = _map_row(raw, cm)
    else:
        mapped = dict(raw) if isinstance(raw, dict) else {}

    name = mapped.get("name") or mapped.get("title") or ""
    if not name:
        return {}

    product_id = mapped.get("id") or mapped.get("sku") or ""
    description = _strip_html(mapped.get("description") or mapped.get("body") or "")
    price, currency = _parse_price(mapped.get("price") or mapped.get("variant_price") or 0)
    image_url = mapped.get("image_url") or mapped.get("image_src") or mapped.get("image")
    url = mapped.get("url") or mapped.get("link")
    brand = mapped.get("brand") or mapped.get("vendor") or ""

    # Availability
    status = str(mapped.get("status") or mapped.get("availability") or "active").lower()
    published = mapped.get("published", "true")
    if isinstance(published, str):
        published_val = published.lower() in ("true", "1", "yes")
    else:
        published_val = bool(published)
    availability = "in_stock" if status == "active" and published_val else "out_of_stock"

    # Capabilities from tags
    tags_str = mapped.get("tags") or ""
    capabilities: List[str] = []
    if tags_str:
        capabilities = [t.strip() for t in tags_str.replace(",", " ").split() if t.strip()][:10]

    return {
        "id": product_id,
        "name": name,
        "description": description,
        "price": price,
        "currency": currency,
        "image_url": image_url,
        "url": url,
        "brand": brand,
        "availability": availability,
        "capabilities": capabilities,
        "metadata": {"source": "legacy_adapter", "product_type": mapped.get("product_type")},
    }


def parse_csv_to_products(
    content: Union[str, bytes],
    column_map: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Parse CSV content into normalized product list.
    Uses first row as headers.
    """
    if isinstance(content, bytes):
        text = content.decode("utf-8", errors="replace")
    else:
        text = content

    reader = csv.DictReader(io.StringIO(text))
    products: List[Dict[str, Any]] = []
    for row in reader:
        if not any(row.values()):
            continue
        p = normalize_legacy_product(dict(row), column_map)
        if p.get("name"):
            products.append(p)
    return products


def parse_json_to_products(
    content: Union[str, bytes, Dict, List],
    column_map: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Parse JSON content into normalized product list.
    Accepts: array of objects, or object with "products"/"items" key.
    """
    if isinstance(content, (dict, list)):
        data = content
    elif isinstance(content, bytes):
        data = json.loads(content.decode("utf-8", errors="replace"))
    else:
        data = json.loads(content)

    items: List[Dict[str, Any]] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("products") or data.get("items") or data.get("data") or [data]

    products: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        p = normalize_legacy_product(item, column_map)
        if p.get("name"):
            products.append(p)
    return products


def parse_excel_to_products(
    content: bytes,
    column_map: Optional[Dict[str, str]] = None,
    sheet_index: int = 0,
) -> List[Dict[str, Any]]:
    """
    Parse Excel (.xlsx) content into normalized product list.
    Uses first sheet, first row as headers.
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl is required for Excel support. Install with: pip install openpyxl")

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
    sheet = wb.worksheets[sheet_index]
    rows = list(sheet.iter_rows(values_only=True))
    wb.close()

    if not rows:
        return []

    headers = [str(h or "").strip() for h in rows[0]]
    products: List[Dict[str, Any]] = []
    for row in rows[1:]:
        row_dict = dict(zip(headers, (v if v is not None else "" for v in row)))
        if not any(row_dict.values()):
            continue
        p = normalize_legacy_product(row_dict, column_map)
        if p.get("name"):
            products.append(p)
    return products
