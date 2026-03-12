"""Local commitment provider: zero tax, no external API. For partners without Shopify/UCP."""

import uuid
from typing import Any, Dict, List, Optional

from .provider import CommitmentProvider, PrecheckResult, CompleteResult


class LocalCommitmentProvider(CommitmentProvider):
    """Local provider: fixed/zero tax, reservation_id is synthetic."""

    @property
    def vendor_type(self) -> str:
        return "local"

    async def precheck(
        self,
        partner_id: str,
        line_items: List[Dict[str, Any]],
        shipping_address: Optional[Dict[str, Any]] = None,
        email: Optional[str] = None,
        name: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> PrecheckResult:
        total = sum(
            float(item.get("price", 0)) * int(item.get("quantity", 1))
            for item in line_items
        )
        reservation_id = f"local-{uuid.uuid4().hex[:12]}"
        return PrecheckResult(
            reservation_id=reservation_id,
            total_price=total,
            total_tax=0.0,
            total_shipping=0.0,
            currency="USD",
        )

    async def complete(
        self,
        partner_id: str,
        reservation_id: str,
        payment_pending: bool = False,
    ) -> CompleteResult:
        if not reservation_id.startswith("local-"):
            raise ValueError("Invalid local reservation_id")
        return CompleteResult(external_order_id=reservation_id)

    async def cancel(
        self,
        partner_id: str,
        external_order_id: str,
    ) -> bool:
        return True
