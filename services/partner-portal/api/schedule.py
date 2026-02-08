"""Schedule (business hours) API."""

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from auth import require_partner_admin
from config import settings
from db import get_partner_by_id, get_partner_schedules, replace_partner_schedules

router = APIRouter(prefix="/api/v1", tags=["Schedule"])


def _base_context(**kwargs):
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


class ScheduleSlot(BaseModel):
    """A single schedule slot."""

    day_of_week: int
    start_time: str
    end_time: str
    timezone: str = "UTC"


class ScheduleReplaceBody(BaseModel):
    """Replace full schedule."""

    schedules: List[ScheduleSlot]


@router.get("/partners/{partner_id}/schedule", response_class=HTMLResponse)
async def schedule_page(request: Request, partner_id: str):
    """Schedule (business hours) editor page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    schedules = await get_partner_schedules(partner_id)
    return templates.TemplateResponse(
        "schedule.html",
        _base_context(request=request, partner=partner, schedules=schedules),
    )


@router.get("/partners/{partner_id}/schedule/list")
async def get_schedule(partner_id: str):
    """List weekly schedule (JSON)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    schedules = await get_partner_schedules(partner_id)
    return {"schedules": schedules}


@router.put("/partners/{partner_id}/schedule")
async def replace_schedule(
    partner_id: str,
    body: ScheduleReplaceBody,
    _: str = Depends(require_partner_admin),
):
    """Replace partner's weekly schedule."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    rows = [
        {
            "day_of_week": s.day_of_week,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "timezone": s.timezone,
        }
        for s in body.schedules
    ]
    ok = await replace_partner_schedules(partner_id, rows)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save schedule")
    return {"message": "Schedule saved", "schedules": rows}
