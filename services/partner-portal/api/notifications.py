"""Notifications API."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from auth import require_partner_admin
from config import settings
from db import get_partner_by_id, list_partner_notifications, mark_notification_read

router = APIRouter(prefix="/api/v1", tags=["Notifications"])


def _base_context(**kwargs):
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


@router.get("/partners/{partner_id}/notifications")
async def get_notifications(
    partner_id: str,
    unread_only: bool = False,
    _: str = Depends(require_partner_admin),
):
    """List notifications (JSON)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    notifications = await list_partner_notifications(
        partner_id, unread_only=unread_only
    )
    return {"notifications": notifications}


@router.patch("/partners/{partner_id}/notifications/{notification_id}/read")
async def mark_read(
    partner_id: str,
    notification_id: str,
    _: str = Depends(require_partner_admin),
):
    """Mark notification as read."""
    ok = await mark_notification_read(notification_id, partner_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}


@router.get("/partners/{partner_id}/notification-preferences")
async def get_preferences(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """Get notification preferences (placeholder)."""
    return {"preferences": []}


@router.put("/partners/{partner_id}/notification-preferences")
async def update_preferences(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """Update notification preferences (placeholder)."""
    return {"message": "Preferences updated"}
