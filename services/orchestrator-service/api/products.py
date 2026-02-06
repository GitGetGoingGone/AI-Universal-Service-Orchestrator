"""Product and bundle API - proxies to Discovery service."""

from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from clients import get_product_details, add_to_bundle as add_to_bundle_client

router = APIRouter(prefix="/api/v1", tags=["Products"])


@router.get("/products/{product_id}")
async def get_product(product_id: str):
    """Get product by ID. For View Details action."""
    try:
        return await get_product_details(product_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Product not found")
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")


class AddToBundleBody(BaseModel):
    """Request body for adding a product to a bundle."""

    product_id: str
    user_id: Optional[str] = None
    bundle_id: Optional[str] = None


@router.post("/bundle/add")
async def add_to_bundle(body: AddToBundleBody):
    """Add product to bundle. For Add to Bundle action."""
    try:
        return await add_to_bundle_client(
            product_id=body.product_id,
            user_id=body.user_id,
            bundle_id=body.bundle_id,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Product not found")
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")
