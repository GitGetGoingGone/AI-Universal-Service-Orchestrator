"""
Google Universal Commerce Protocol (UCP) product/item compliance.

UCP defines product representation in checkout/order flows (Item Response):
https://ucp.dev/specification/reference/ (Item Response, Line Item Response)
- id (required): recognized by Platform and Business; for Google must match product feed id
- title (required)
- price (required): integer, minor units (cents)
- image_url (optional)

UCP does not publish a separate "product feed spec" like ACP; catalog is discovered
via /.well-known/ucp and business endpoints. Item in checkout must have id, title, price.
"""

from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# UCP Item Response required fields (product in checkout/catalog context)
# https://ucp.dev/specification/reference/#item-response
# ---------------------------------------------------------------------------
UCP_ITEM_REQUIRED_FIELDS = frozenset({
    "id",      # required, unique, must match product feed for Google
    "title",   # required (we accept "name" as alias)
    "price",   # required, integer minor units (cents)
})
UCP_ITEM_OPTIONAL = frozenset({"image_url"})

# Reuse same prohibited content policy as ACP for consistency (both are AI commerce surfaces)
from .acp_compliance import validate_acp_prohibited_content


def _normalize_for_ucp(product: Dict[str, Any]) -> Dict[str, Any]:
    """Map our internal shape to UCP field names."""
    p = dict(product)
    if "name" in p and "title" not in p:
        p["title"] = p["name"]
    if "id" not in p and "item_id" in p:
        p["id"] = str(p["item_id"])
    return p


def validate_ucp_item_required_fields(product: Dict[str, Any]) -> List[str]:
    """
    Validate that product has UCP Item required fields (id, title, price).
    Price can be number (we treat as major units) or integer cents; UCP expects integer cents.
    Returns list of missing field names.
    """
    p = _normalize_for_ucp(product)
    missing = []

    if not p.get("id") and not p.get("item_id"):
        missing.append("id")
    if not (p.get("title") or p.get("name")):
        missing.append("title")
    if p.get("price") is None:
        missing.append("price")
    elif isinstance(p.get("price"), (int, float)) and float(p["price"]) < 0:
        missing.append("price")  # invalid

    return missing


def validate_product_ucp(product: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    UCP compliance check for one product (Item).
    Returns (is_compliant, missing_fields, prohibited_violations).
    Prohibited content uses shared policy (ACP blocklist).
    """
    missing = validate_ucp_item_required_fields(product)
    violations = validate_acp_prohibited_content(product)
    is_compliant = len(missing) == 0 and len(violations) == 0
    return is_compliant, missing, violations


def filter_ucp_compliant_products(
    products: List[Dict[str, Any]],
    strict: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split products into UCP-compliant vs non-compliant. Returns (compliant, non_compliant)."""
    compliant = []
    non_compliant = []
    for p in products:
        ok, missing, violations = validate_product_ucp(p)
        if strict and violations:
            non_compliant.append({**p, "_ucp_errors": {"missing": missing, "prohibited": violations}})
        elif missing or violations:
            non_compliant.append({**p, "_ucp_errors": {"missing": missing, "prohibited": violations}})
        else:
            compliant.append(p)
    return compliant, non_compliant
