"""
Commitment providers for payment-service: Shopify, Local.
Registers providers with shared commitment registry.
"""

import sys
from pathlib import Path

# Add repo root for shared package
_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from typing import Any, Dict, List, Optional

from packages.shared.commitment import (
    CommitmentProvider,
    PrecheckResult,
    CompleteResult,
    register_provider,
)
from shopify_draft import (
    create_draft_order_precheck,
    complete_draft_order,
    cancel_shopify_order,
    get_shopify_partner_credentials,
)


class ShopifyCommitmentProvider(CommitmentProvider):
    """Shopify draft order commitment provider."""

    @property
    def vendor_type(self) -> str:
        return "shopify"

    async def precheck(
        self,
        partner_id: str,
        line_items: List[Dict[str, Any]],
        shipping_address: Optional[Dict[str, Any]] = None,
        email: Optional[str] = None,
        name: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> PrecheckResult:
        creds = get_shopify_partner_credentials(partner_id)
        if not creds:
            raise ValueError(f"No Shopify credentials for partner {partner_id}")

        result = await create_draft_order_precheck(
            shop_url=creds["shop_url"],
            access_token=creds["access_token"],
            line_items=line_items,
            shipping_address=shipping_address,
            email=email,
            name=name,
            phone=phone,
        )
        return PrecheckResult(
            reservation_id=str(result.get("draft_order_id", "")),
            total_price=float(result.get("total_price", 0)),
            total_tax=float(result.get("total_tax", 0)),
            currency=result.get("currency", "USD"),
            raw=result,
        )

    async def complete(
        self,
        partner_id: str,
        reservation_id: str,
        payment_pending: bool = False,
    ) -> CompleteResult:
        creds = get_shopify_partner_credentials(partner_id)
        if not creds:
            raise ValueError(f"No Shopify credentials for partner {partner_id}")

        result = await complete_draft_order(
            shop_url=creds["shop_url"],
            access_token=creds["access_token"],
            draft_order_id=reservation_id,
            payment_pending=payment_pending,
        )
        if result.get("error"):
            raise ValueError(result["error"])
        order_id = result.get("order_id")
        if not order_id:
            raise ValueError("Shopify complete returned no order_id")
        return CompleteResult(external_order_id=str(order_id), raw=result)

    async def cancel(
        self,
        partner_id: str,
        external_order_id: str,
    ) -> bool:
        creds = get_shopify_partner_credentials(partner_id)
        if not creds:
            return False
        return await cancel_shopify_order(
            shop_url=creds["shop_url"],
            access_token=creds["access_token"],
            order_id=external_order_id,
        )


def _register_commitment_providers() -> None:
    """Register Shopify and Local providers. Call at app startup."""
    from packages.shared.commitment.local_provider import LocalCommitmentProvider

    register_provider(ShopifyCommitmentProvider())
    register_provider(LocalCommitmentProvider())


# Register on import
_register_commitment_providers()
