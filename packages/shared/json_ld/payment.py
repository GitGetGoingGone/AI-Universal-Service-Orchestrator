"""Schema.org JSON-LD for Payment."""

from typing import Any, Dict, Optional


def payment_ld(
    payment_id: str,
    status: Optional[str] = None,
    amount: Optional[float] = None,
    currency: str = "USD",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Payment as Schema.org Payment."""
    out: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Payment",
        "identifier": payment_id,
    }
    if status:
        out["paymentStatus"] = status
    if amount is not None:
        out["amount"] = {"@type": "MonetaryAmount", "value": amount, "currency": currency}
    out.update(kwargs)
    return out
