"""Admin management API - partner admins and platform admins."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from auth import require_partner_admin, require_partner_owner, require_platform_admin
from config import settings
from db import (
    add_platform_admin,
    get_partner_by_id,
    list_partner_admins,
    list_partner_members,
    list_partners,
    list_platform_admins,
    update_partner_member,
)

router = APIRouter(prefix="/api/v1", tags=["Admins"])


def _base_context(**kwargs):
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


class PromoteAdminBody(BaseModel):
    """Promote member to admin."""

    member_id: str


class PlatformAdminBody(BaseModel):
    """Add platform admin."""

    user_id: str
    scope: str = "all"


@router.get("/partners/{partner_id}/admins", response_class=HTMLResponse)
async def admins_page(request: Request, partner_id: str):
    """Partner admins management page (owner only for promote/revoke)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    admins = await list_partner_admins(partner_id)
    members = await list_partner_members(partner_id)
    promotable = [m for m in members if m.get("role") not in ("owner", "admin") and m.get("is_active")]
    return templates.TemplateResponse(
        "admins.html",
        _base_context(request=request, partner=partner, admins=admins, promotable=promotable),
    )


@router.get("/partners/{partner_id}/admins/list")
async def list_admins(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """List partner admins (owner/admin roles)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    admins = await list_partner_admins(partner_id)
    return {"admins": admins}


@router.post("/partners/{partner_id}/admins")
async def promote_admin(
    partner_id: str,
    body: PromoteAdminBody,
    _: str = Depends(require_partner_owner),
):
    """Promote member to admin (owner only)."""
    result = await update_partner_member(body.member_id, partner_id, role="admin")
    if not result:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"message": "Member promoted to admin", "member_id": body.member_id}


@router.delete("/partners/{partner_id}/admins/{member_id}")
async def revoke_admin(
    partner_id: str,
    member_id: str,
    _: str = Depends(require_partner_owner),
):
    """Revoke admin (downgrade to member)."""
    result = await update_partner_member(member_id, partner_id, role="member")
    if not result:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"message": "Admin revoked", "member_id": member_id}


# --- Platform admin ---
@router.get("/platform/partners")
async def platform_list_partners(
    _: str = Depends(require_platform_admin),
):
    """List all partners (platform admin only)."""
    partners = await list_partners(limit=100)
    return {"partners": partners}


@router.get("/platform", response_class=HTMLResponse)
async def platform_admin_page(request: Request):
    """Platform admin page - list partners, manage platform admins."""
    return templates.TemplateResponse(
        "platform_admin.html",
        _base_context(request=request),
    )


@router.get("/platform/admins")
async def platform_list_admins(
    _: str = Depends(require_platform_admin),
):
    """List platform admins."""
    admins = await list_platform_admins()
    return {"admins": admins}


@router.post("/platform/admins")
async def platform_add_admin(
    body: PlatformAdminBody,
    _: str = Depends(require_platform_admin),
):
    """Add platform admin."""
    admin = await add_platform_admin(body.user_id, body.scope)
    if not admin:
        raise HTTPException(status_code=500, detail="Failed to add platform admin")
    return {"message": "Platform admin added", "admin_id": str(admin["id"])}
