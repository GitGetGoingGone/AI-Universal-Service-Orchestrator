"""Delivery buffer logic - Pillar 4. Adds buffer to delivery windows."""

from datetime import datetime, timedelta
from typing import Optional


def apply_delivery_buffer(
    window_start: datetime,
    window_end: datetime,
    buffer_minutes: int = 15,
) -> tuple[datetime, datetime]:
    """
    Apply buffer to delivery window. Default +15 min to end.
    Returns (window_start, window_end_with_buffer).
    """
    buffered_end = window_end + timedelta(minutes=buffer_minutes)
    return (window_start, buffered_end)


def get_buffer_minutes_from_env() -> int:
    """Get buffer minutes from env (fallback 15)."""
    import os
    v = os.getenv("DELIVERY_BUFFER_MINUTES", "15")
    try:
        return max(0, int(v))
    except ValueError:
        return 15
