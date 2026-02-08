"""Team members API."""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from auth import require_partner_admin
from config import settings
from db import (
    add_partner_member,
    get_partner_by_id,
    list_partner_members,
    update_partner_member,
)

router = APIRouter(prefix="/api/v1", tags=["Team"])


def _base_context(**kwargs):
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


class TeamMemberBody(BaseModel):
    """Add team member."""

    email: str
    role: str = "member"
    display_name: Optional[str] = None


class TeamMemberUpdateBody(BaseModel):
    """Update team member."""

    role: Optional[str] = None
    display_name: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/partners/{partner_id}/team", response_class=HTMLResponse)
async def team_page(request: Request, partner_id: str):
    """Team members page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    members = await list_partner_members(partner_id)
    return templates.TemplateResponse(
        "team.html",
        _base_context(request=request, partner=partner, members=members),
    )


@router.get("/partners/{partner_id}/team/list")
async def get_team(partner_id: str):
    """List team members (JSON)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    members = await list_partner_members(partner_id)
    return {"members": members}


@router.post("/partners/{partner_id}/team")
async def add_member(
    partner_id: str,
    body: TeamMemberBody,
    _: str = Depends(require_partner_admin),
):
    """Add team member (invite or record-only)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    member = await add_partner_member(
        partner_id=partner_id,
        email=body.email,
        role=body.role,
        display_name=body.display_name,
    )
    if not member:
        raise HTTPException(status_code=500, detail="Failed to add member")
    return {"member_id": str(member["id"]), "message": "Member added"}


@router.patch("/partners/{partner_id}/team/{member_id}")
async def update_member(
    partner_id: str,
    member_id: str,
    body: TeamMemberUpdateBody,
    _: str = Depends(require_partner_admin),
):
    """Update team member role or status."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return {"message": "No updates", "member_id": member_id}
    result = await update_partner_member(member_id, partner_id, **updates)
    if not result:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"message": "Member updated", "member_id": member_id}


@router.delete("/partners/{partner_id}/team/{member_id}")
async def remove_member(
    partner_id: str,
    member_id: str,
    _: str = Depends(require_partner_admin),
):
    """Deactivate team member (soft delete)."""
    result = await update_partner_member(member_id, partner_id, is_active=False)
    if not result:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"message": "Member deactivated", "member_id": member_id}
