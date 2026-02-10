"""
OpenAI Product Feed Spec compliance (https://developers.openai.com/commerce/specs/feed).

Validates product records against required fields, validation rules, and Prohibited Products Policy.
Use on manifest ingest, before export to ChatGPT, or in partner portal when marking "ACP eligible".
"""

from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Required fields per OpenAI Product Feed Spec (Basic + eligibility + merchant)
# https://developers.openai.com/commerce/specs/feed
# ---------------------------------------------------------------------------
ACP_REQUIRED_FIELDS = frozenset({
    "item_id",           # or id – merchant product ID, max 100 chars, stable
    "title",            # or name – max 150 chars
    "description",      # max 5000 chars, plain text
    "url",              # product detail page URL, HTTP 200, HTTPS preferred
    "image_url",        # main product image URL
    "price",            # number + currency (e.g. "79.99 USD")
    "availability",     # in_stock | out_of_stock | pre_order | backorder | unknown
    "brand",            # max 70 chars
    "is_eligible_search",
    "is_eligible_checkout",
    "seller_name",      # max 70 chars
    "seller_url",       # HTTPS preferred
    "return_policy",    # URL, HTTPS preferred
    "target_countries", # list, ISO 3166-1 alpha-2
    "store_country",    # ISO 3166-1 alpha-2
})
# If is_eligible_checkout is true, also required:
ACP_CHECKOUT_REQUIRED = frozenset({"seller_privacy_policy", "seller_tos"})

# Variants (if listing has variations):
ACP_VARIANT_REQUIRED = frozenset({"group_id", "listing_has_variations"})

# Prohibited Products Policy – categories/keywords that indicate non-compliant content
# https://developers.openai.com/commerce/specs/feed (Prohibited Products Policy)
ACP_PROHIBITED_CATEGORIES = frozenset({
    "adult", "alcohol", "nicotine", "tobacco", "cigarette", "vape", "gambling",
    "weapon", "firearm", "ammunition", "explosive", "prescription", "medication",
    "cbd", "cannabis", "illegal", "counterfeit", "stolen",
})
# Substrings to flag in title/description (case-insensitive)
ACP_PROHIBITED_KEYWORDS = frozenset({
    "adult only", "18+", "21+", "alcohol", "beer", "wine", "spirits",
    "nicotine", "vape", "e-cigarette", "tobacco", "gambling", "casino", "lottery",
    "weapon", "gun", "ammo", "firearm", "prescription", "rx only", "cbd", "thc",
})


def _normalize_product_for_validation(product: Dict[str, Any]) -> Dict[str, Any]:
    """Map our internal product shape to ACP field names for validation."""
    # We use name/id; ACP uses title/item_id. Normalize for checks.
    p = dict(product)
    if "name" in p and "title" not in p:
        p["title"] = p["name"]
    if "id" in p and "item_id" not in p:
        p["item_id"] = str(p["id"])
    if "image" in p and "image_url" not in p:
        p["image_url"] = p.get("image")
    return p


def validate_acp_required_fields(
    product: Dict[str, Any],
    *,
    require_checkout_fields: bool = False,
    is_variant: bool = False,
) -> List[str]:
    """
    Validate that product has all ACP required fields.
    Returns list of missing field names (empty if compliant).
    """
    p = _normalize_product_for_validation(product)
    missing = []

    for field in ACP_REQUIRED_FIELDS:
        val = p.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)

    if require_checkout_fields and p.get("is_eligible_checkout") in (True, "true", "1"):
        for field in ACP_CHECKOUT_REQUIRED:
            val = p.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append(field)

    if is_variant:
        for field in ACP_VARIANT_REQUIRED:
            val = p.get(field)
            if val is None:
                missing.append(field)

    return missing


def validate_acp_prohibited_content(product: Dict[str, Any]) -> List[str]:
    """
    Check product against Prohibited Products Policy (adult, alcohol, weapons, etc.).
    Returns list of violation descriptions (empty if compliant).
    """
    p = _normalize_product_for_validation(product)
    violations = []

    title = (p.get("title") or p.get("name") or "").lower()
    description = (p.get("description") or "").lower()
    category = (p.get("product_category") or p.get("category") or "").lower()
    brand = (p.get("brand") or "").lower()
    combined = " ".join([title, description, category, brand])

    for kw in ACP_PROHIBITED_KEYWORDS:
        if kw in combined:
            violations.append(f"Prohibited content detected: '{kw}'")

    for cat in ACP_PROHIBITED_CATEGORIES:
        if cat in combined:
            violations.append(f"Prohibited category detected: '{cat}'")

    return violations


def validate_product_acp(
    product: Dict[str, Any],
    *,
    require_checkout_fields: bool = False,
    is_variant: bool = False,
) -> Tuple[bool, List[str], List[str]]:
    """
    Full ACP compliance check for one product.
    Returns (is_compliant, missing_fields, prohibited_violations).
    """
    missing = validate_acp_required_fields(
        product,
        require_checkout_fields=require_checkout_fields,
        is_variant=is_variant,
    )
    violations = validate_acp_prohibited_content(product)
    is_compliant = len(missing) == 0 and len(violations) == 0
    return is_compliant, missing, violations


def filter_acp_compliant_products(
    products: List[Dict[str, Any]],
    *,
    require_checkout_fields: bool = False,
    strict: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Split products into compliant vs non-compliant.
    If strict=True, prohibited content excludes the product; if False, only missing required fields exclude.
    Returns (compliant_list, non_compliant_list).
    """
    compliant = []
    non_compliant = []
    for p in products:
        ok, missing, violations = validate_product_acp(
            p, require_checkout_fields=require_checkout_fields
        )
        if strict and violations:
            non_compliant.append({**p, "_acp_errors": {"missing": missing, "prohibited": violations}})
        elif missing or violations:
            non_compliant.append({**p, "_acp_errors": {"missing": missing, "prohibited": violations}})
        else:
            compliant.append(p)
    return compliant, non_compliant
