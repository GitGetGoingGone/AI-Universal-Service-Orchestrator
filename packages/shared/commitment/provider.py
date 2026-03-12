"""
Commitment provider interface: vendor-agnostic precheck, complete, cancel, place.
All vendor-specific behavior (Shopify draft orders, UCP reserve/commit) lives behind this interface.
Gateway, payment-service webhook, and re-sourcing call this; they never branch on vendor type.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Provider registry: vendor_type -> implementation
_PROVIDERS: Dict[str, "CommitmentProvider"] = {}


@dataclass
class PrecheckResult:
    """Result from commitment precheck (draft/reserve)."""

    reservation_id: str
    total_price: float
    total_tax: float = 0.0
    total_shipping: float = 0.0
    currency: str = "USD"
    raw: Optional[Dict[str, Any]] = None


@dataclass
class CompleteResult:
    """Result from commitment complete (convert draft/reserve to order)."""

    external_order_id: str
    raw: Optional[Dict[str, Any]] = None


class CommitmentProvider(ABC):
    """Abstract commitment provider. Implement for each vendor type (shopify, ucp, local)."""

    @property
    @abstractmethod
    def vendor_type(self) -> str:
        """Vendor type identifier (shopify, ucp, local)."""
        ...

    @abstractmethod
    async def precheck(
        self,
        partner_id: str,
        line_items: List[Dict[str, Any]],
        shipping_address: Optional[Dict[str, Any]] = None,
        email: Optional[str] = None,
        name: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> PrecheckResult:
        """
        Create draft/reservation; return TCO. Do NOT complete.
        """
        ...

    @abstractmethod
    async def complete(
        self,
        partner_id: str,
        reservation_id: str,
        payment_pending: bool = False,
    ) -> CompleteResult:
        """
        Complete draft/reservation after payment. Returns external_order_id.
        """
        ...

    @abstractmethod
    async def cancel(
        self,
        partner_id: str,
        external_order_id: str,
    ) -> bool:
        """
        Cancel order/draft at vendor. Returns True on success.
        """
        ...


def register_provider(provider: CommitmentProvider) -> None:
    """Register a commitment provider for its vendor_type."""
    _PROVIDERS[provider.vendor_type] = provider


def get_provider(vendor_type: str) -> Optional[CommitmentProvider]:
    """Get commitment provider by vendor_type. Returns None if not registered."""
    return _PROVIDERS.get(vendor_type)


def get_vendor_type_for_partner(transport_type: Optional[str], commitment_vendor_type: Optional[str]) -> str:
    """
    Resolve vendor_type from partner config.
    commitment_vendor_type overrides transport_type. Defaults to 'local'.
    """
    if commitment_vendor_type:
        v = str(commitment_vendor_type).strip().lower()
        if v in ("shopify", "ucp", "local"):
            return v
    if transport_type:
        t = str(transport_type).strip().upper()
        if t == "SHOPIFY":
            return "shopify"
        if t in ("UCP", "MCP"):
            return "ucp"
    return "local"
