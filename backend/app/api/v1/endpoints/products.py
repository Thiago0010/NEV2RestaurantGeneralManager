from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.api.deps import get_db, get_current_active_user, get_restaurant_from_user
from app.schemas import (
    ProductCreate, ProductUpdate, ProductRead,
    PaginatedResponse
)
from app.services.crud import ProductService
from app.models import Restaurant

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new product"""
    service = ProductService(db)
    product = await service.create(data, restaurant.id)
    return ProductRead.model_validate(product)


@router.get("", response_model=PaginatedResponse)
async def list_products(
    category_id: Optional[UUID] = None,
    available_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """List all products"""
    service = ProductService(db)
    products, total = await service.list(
        restaurant.id,
        category_id=category_id,
        available_only=available_only,
        page=page,
        page_size=page_size
    )
    
    return PaginatedResponse(
        items=[ProductRead.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: UUID,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a product by ID"""
    service = ProductService(db)
    product = await service.get_by_id(product_id, restaurant.id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductRead.model_validate(product)


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    current_user = Depends(get_current_active_user),
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a product"""
    service = ProductService(db)
    product = await service.update(product_id, restaurant.id, current_user.id, data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductRead.model_validate(product)


@router.patch("/{product_id}/toggle/{field}", response_model=ProductRead)
async def toggle_product_field(
    product_id: UUID,
    field: str,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle a boolean field (available, featured)"""
    if field not in ["available", "featured"]:
        raise HTTPException(status_code=400, detail="Invalid field")
    
    service = ProductService(db)
    product = await service.toggle_field(product_id, restaurant.id, field)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductRead.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    current_user = Depends(get_current_active_user),
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a product"""
    service = ProductService(db)
    success = await service.delete(product_id, restaurant.id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")