"""Partner (seller) discovery validation API."""

from fastapi import APIRouter, HTTPException

from db import get_partner_by_id

router = APIRouter(prefix="/api/v1/partners", tags=["Partners"])

# ACP seller-level required fields (partner must have these for products to be ACP compliant)
PARTNER_ACP_SELLER_FIELDS = [
    ("seller_name", "Seller name (or business name)"),
    ("seller_url", "Seller URL"),
    ("return_policy_url", "Return policy URL"),
    ("store_country", "Store country (ISO 3166-1 alpha-2)"),
    ("target_countries", "Target countries (list or at least one)"),
]


@router.get("/{partner_id}/validate-discovery")
async def validate_partner_discovery(partner_id: str):
    """
    Validate partner commerce profile for ACP (ChatGPT) discovery.
    Checks that seller-level required fields are set so products can be included in the feed.
    Returns { acp: { valid, errors, warnings } }.
    """
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    errors = []
    for key, label in PARTNER_ACP_SELLER_FIELDS:
        val = partner.get(key)
        if key == "seller_name":
            val = val or partner.get("business_name")
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"Missing: {label}")
        elif key == "target_countries" and isinstance(val, list) and len(val) == 0:
            errors.append(f"Missing: {label}")
    valid = len(errors) == 0
    return {
        "acp": {
            "valid": valid,
            "errors": errors,
            "warnings": [],
        },
    }
