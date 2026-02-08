"""Product registration API."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from auth import require_partner_admin
from config import settings
from db import (
    add_product_assignment,
    add_product_availability,
    create_product,
    delete_product_availability,
    get_partner_by_id,
    get_product_by_id,
    list_partner_members,
    list_product_assignments,
    list_product_availability,
    list_products,
    remove_product_assignment,
    soft_delete_product,
    update_product,
    update_product_availability,
)

router = APIRouter(prefix="/api/v1", tags=["Products"])


def _base_context(**kwargs):
    """Base context for all templates (theme, layout)."""
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


class ProductBody(BaseModel):
    """Product registration request."""

    name: str
    price: float
    description: Optional[str] = None
    currency: str = "USD"
    capabilities: Optional[List[str]] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    image_url: Optional[str] = None
    category_id: Optional[str] = None
    is_available: bool = True


class ProductUpdateBody(BaseModel):
    """Product update (partial)."""

    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    image_url: Optional[str] = None
    category_id: Optional[str] = None
    is_available: Optional[bool] = None


class AvailabilityBody(BaseModel):
    """Add availability slot."""

    slot_type: str = "date_range"
    start_at: str
    end_at: str
    capacity: int = 1
    booking_mode: str = "auto_book"
    timezone: str = "UTC"


class AvailabilityUpdateBody(BaseModel):
    """Update availability slot (partial)."""

    start_at: Optional[str] = None
    end_at: Optional[str] = None
    capacity: Optional[int] = None
    booking_mode: Optional[str] = None


class AssignmentBody(BaseModel):
    """Assign team member to product."""

    partner_member_id: str
    role: str = "handler"


@router.get("/partners/{partner_id}/products", response_class=HTMLResponse)
async def products_page(request: Request, partner_id: str):
    """Product registration page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    products = await list_products(partner_id)
    return templates.TemplateResponse(
        "products.html",
        _base_context(request=request, partner=partner, products=products),
    )


@router.get("/partners/{partner_id}/products/{product_id}", response_class=HTMLResponse)
async def product_detail_page(request: Request, partner_id: str, product_id: str):
    """Product detail page with availability scheduling."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    product = await get_product_by_id(product_id, partner_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    availability = await list_product_availability(product_id)
    assignments = await list_product_assignments(product_id)
    members = await list_partner_members(partner_id)
    return templates.TemplateResponse(
        "product_detail.html",
        _base_context(
            request=request,
            partner=partner,
            product=product,
            availability=availability,
            assignments=assignments,
            members=members,
        ),
    )


@router.get("/partners/{partner_id}/products/list")
async def get_partner_products(partner_id: str):
    """List products for a partner (JSON API)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    products = await list_products(partner_id)
    return {"products": products}


@router.post("/partners/{partner_id}/products")
async def add_product(partner_id: str, body: ProductBody):
    """Register a new product for a partner."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    product = await create_product(
        partner_id=partner_id,
        name=body.name,
        price=body.price,
        description=body.description,
        currency=body.currency,
        capabilities=body.capabilities,
        price_min=body.price_min,
        price_max=body.price_max,
        image_url=body.image_url,
        category_id=body.category_id,
        is_available=body.is_available,
    )
    if not product:
        raise HTTPException(status_code=500, detail="Failed to create product")
    return {"product_id": str(product["id"]), "message": "Product created successfully"}


@router.patch("/partners/{partner_id}/products/{product_id}")
async def update_product_endpoint(
    partner_id: str,
    product_id: str,
    body: ProductUpdateBody,
    _: str = Depends(require_partner_admin),
):
    """Update a product."""
    product = await get_product_by_id(product_id, partner_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    updates = body.model_dump(exclude_unset=True)
    result = await update_product(product_id, partner_id, **updates)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update product")
    return {"message": "Product updated", "product_id": product_id}


@router.delete("/partners/{partner_id}/products/{product_id}")
async def delete_product_endpoint(
    partner_id: str,
    product_id: str,
    _: str = Depends(require_partner_admin),
):
    """Soft delete a product."""
    product = await get_product_by_id(product_id, partner_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    ok = await soft_delete_product(product_id, partner_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete product")
    return {"message": "Product deleted", "product_id": product_id}


# --- Availability ---
@router.get("/partners/{partner_id}/products/{product_id}/availability")
async def get_product_availability(partner_id: str, product_id: str):
    """List availability slots for a product."""
    product = await get_product_by_id(product_id, partner_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    slots = await list_product_availability(product_id)
    return {"availability": slots}


@router.post("/partners/{partner_id}/products/{product_id}/availability")
async def add_availability_slot(
    partner_id: str,
    product_id: str,
    body: AvailabilityBody,
    _: str = Depends(require_partner_admin),
):
    """Add availability slot."""
    product = await get_product_by_id(product_id, partner_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    slot = await add_product_availability(
        product_id=product_id,
        slot_type=body.slot_type,
        start_at=body.start_at,
        end_at=body.end_at,
        capacity=body.capacity,
        booking_mode=body.booking_mode,
        timezone=body.timezone,
    )
    if not slot:
        raise HTTPException(status_code=500, detail="Failed to add slot")
    return {"slot_id": str(slot["id"]), "message": "Slot added"}


@router.patch("/partners/{partner_id}/products/{product_id}/availability/{slot_id}")
async def update_availability_slot(
    partner_id: str,
    product_id: str,
    slot_id: str,
    body: AvailabilityUpdateBody,
    _: str = Depends(require_partner_admin),
):
    """Update availability slot."""
    product = await get_product_by_id(product_id, partner_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return {"message": "No updates", "slot_id": slot_id}
    result = await update_product_availability(slot_id, **updates)
    if not result:
        raise HTTPException(status_code=404, detail="Slot not found")
    return {"message": "Slot updated", "slot_id": slot_id}


@router.delete("/partners/{partner_id}/products/{product_id}/availability/{slot_id}")
async def delete_availability_slot(
    partner_id: str,
    product_id: str,
    slot_id: str,
    _: str = Depends(require_partner_admin),
):
    """Delete availability slot."""
    product = await get_product_by_id(product_id, partner_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    ok = await delete_product_availability(slot_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Slot not found")
    return {"message": "Slot deleted"}


# --- Assignments ---
@router.get("/partners/{partner_id}/products/{product_id}/assignments")
async def get_product_assignments(partner_id: str, product_id: str):
    """List team members assigned to product."""
    product = await get_product_by_id(product_id, partner_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    assignments = await list_product_assignments(product_id)
    return {"assignments": assignments}


@router.post("/partners/{partner_id}/products/{product_id}/assignments")
async def add_assignment(
    partner_id: str,
    product_id: str,
    body: AssignmentBody,
    _: str = Depends(require_partner_admin),
):
    """Assign team member to product."""
    product = await get_product_by_id(product_id, partner_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    result = await add_product_assignment(
        product_id=product_id,
        partner_member_id=body.partner_member_id,
        role=body.role,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to add assignment")
    return {"message": "Assignment added"}


@router.delete("/partners/{partner_id}/products/{product_id}/assignments/{member_id}")
async def remove_assignment(
    partner_id: str,
    product_id: str,
    member_id: str,
    _: str = Depends(require_partner_admin),
):
    """Remove team member from product."""
    product = await get_product_by_id(product_id, partner_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    ok = await remove_product_assignment(product_id, member_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return {"message": "Assignment removed"}
