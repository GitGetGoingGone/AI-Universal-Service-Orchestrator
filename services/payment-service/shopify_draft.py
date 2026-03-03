"""
Shopify Draft Order integration for Gateway-to-Shopify payment flow (Phase 5).
- Pre-check: create draft, return total_price, total_tax, total_shipping for TCO display
- Complete: mark draft as paid after Stripe charge success
- Error handling: partial refund and leg status update on complete failure
"""

from typing import Any, Dict, List, Optional

import httpx

SHOPIFY_API_VERSION = "2024-10"


def _shopify_admin_url(shop_url: str, path: str) -> str:
    """Build Shopify Admin REST URL."""
    base = str(shop_url).rstrip("/").replace("https://", "").replace("http://", "").split("/")[0]
    return f"https://{base}/admin/api/{SHOPIFY_API_VERSION}{path}"


async def create_draft_order_precheck(
    shop_url: str,
    access_token: str,
    line_items: List[Dict[str, Any]],
    shipping_address: Optional[Dict[str, Any]] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    phone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create Shopify Draft Order (status=open), do NOT complete.
    Returns total_price, total_tax, currency, draft_order_id.
    Use to show exact TCO before charging user via Stripe.
    """
    addr = dict(shipping_address or {})
    if name and ("first_name" not in addr or "last_name" not in addr):
        parts = str(name).strip().split(" ", 1)
        addr.setdefault("first_name", parts[0] or "")
        addr.setdefault("last_name", parts[1] if len(parts) > 1 else "")
    if phone:
        addr["phone"] = str(phone)
    payload: Dict[str, Any] = {
        "draft_order": {
            "line_items": [
                {
                    "title": item.get("title", "Item"),
                    "price": str(item.get("price", "0")),
                    "quantity": int(item.get("quantity", 1)),
                    "taxable": item.get("taxable", True),
                }
                for item in line_items
            ],
        }
    }
    if addr:
        payload["draft_order"]["shipping_address"] = addr
    if email:
        payload["draft_order"]["email"] = email

    url = _shopify_admin_url(shop_url, "/draft_orders.json")
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    draft = data.get("draft_order", {})
    return {
        "draft_order_id": str(draft.get("id", "")),
        "total_price": float(draft.get("total_price", 0) or 0),
        "total_tax": float(draft.get("total_tax", 0) or 0),
        "currency": draft.get("currency", "USD"),
    }


async def complete_draft_order(
    shop_url: str,
    access_token: str,
    draft_order_id: str,
    payment_pending: bool = False,
) -> Dict[str, Any]:
    """
    Complete a Shopify Draft Order (creates the order).
    Call after Stripe charge succeeds. Use payment_pending=false to mark as paid.
    Returns order_id or error.
    """
    url = _shopify_admin_url(shop_url, f"/draft_orders/{draft_order_id}/complete.json")
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token,
    }
    payload = {"payment_pending": payment_pending}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.put(url, json=payload, headers=headers)
    if resp.status_code >= 400:
        return {
            "error": resp.text or "Complete failed",
            "status_code": resp.status_code,
            "order_id": None,
        }
    data = resp.json()
    draft = data.get("draft_order", {})
    order_id = draft.get("order_id")
    return {
        "order_id": str(order_id) if order_id else None,
        "error": None,
    }


async def get_shopify_partner_credentials(partner_id: str) -> Optional[Dict[str, str]]:
    """
    Get shop_url and access_token for a Shopify curated partner.
    Returns { shop_url, access_token } or None.
    """
    from db import get_supabase

    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("shopify_curated_partners")
            .select("shop_url, access_token_vault_ref")
            .eq("partner_id", partner_id)
            .limit(1)
            .execute()
        )
        row = result.data[0] if result.data else None
        if not row or not row.get("access_token_vault_ref"):
            return None
        vault_ref = row.get("access_token_vault_ref")
        token_rpc = client.rpc("get_shopify_token", {"vault_ref": str(vault_ref)}).execute()
        token = token_rpc.data if isinstance(token_rpc.data, str) else None
        if not token:
            return None
        return {
            "shop_url": str(row.get("shop_url", "")),
            "access_token": str(token),
        }
    except Exception:
        return None
