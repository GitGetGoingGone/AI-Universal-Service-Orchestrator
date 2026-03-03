"""Shared schemas for Gateway, Discovery, and Payment services."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class StandardizedShipping(BaseModel):
    """
    Standardized shipping address for checkout and Shopify Draft Orders.
    Collected at Gateway before payment; passed to Draft Order creation.
    """

    name: str = Field(..., description="Full name of recipient")
    address: Dict[str, Any] = Field(
        ...,
        description="Address fields: street_address, locality, region, postal_code, country",
    )
    phone: Optional[str] = None
    email: str = Field(..., description="Email for order confirmation")

    def to_shopify_shipping_address(self) -> Dict[str, Any]:
        """Convert to Shopify shipping_address format."""
        addr = self.address or {}
        parts = str(self.name or "").split(" ", 1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""
        return {
            "first_name": first_name,
            "last_name": last_name,
            "address1": addr.get("street_address") or addr.get("address1") or "",
            "address2": addr.get("address2") or "",
            "city": addr.get("locality") or addr.get("city") or "",
            "province": addr.get("region") or addr.get("province") or "",
            "province_code": addr.get("region_code") or addr.get("province_code") or "",
            "country": addr.get("country") or "",
            "country_code": addr.get("country_code") or (addr.get("country") or "")[:2].upper(),
            "zip": addr.get("postal_code") or addr.get("zip") or "",
            "phone": self.phone or "",
        }
