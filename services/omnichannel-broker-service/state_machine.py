"""Negotiation state machine."""

from typing import Optional

VALID_STATUSES = {"pending", "awaiting_partner_reply", "accepted", "rejected", "counter_offer", "escalated"}


def can_transition(current: str, new: str) -> bool:
    """Check if transition from current to new is valid."""
    if new not in VALID_STATUSES:
        return False
    transitions = {
        "pending": {"awaiting_partner_reply"},
        "awaiting_partner_reply": {"accepted", "rejected", "counter_offer", "escalated"},
        "accepted": set(),
        "rejected": set(),
        "counter_offer": {"awaiting_partner_reply", "accepted", "rejected"},
        "escalated": set(),
    }
    return new in transitions.get(current, set())
