from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.api.deps import get_db, get_current_active_user, get_restaurant_from_user
from app.schemas import (
    CategoryCreate, CategoryUpdate, CategoryRead,
    PaginatedResponse
)
from app.services.crud import CategoryService
from app.models import Restaurant

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new category"""
    service = CategoryService(db)
    category = await service.create(data, restaurant.id)
    return CategoryRead.model_validate(category)


@router.get("", response_model=PaginatedResponse)
async def list_categories(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """List all categories"""
    service = CategoryService(db)
    categories, total = await service.list(restaurant.id, page, page_size)
    
    return PaginatedResponse(
        items=[CategoryRead.model_validate(c) for c in categories],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: UUID,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a category by ID"""
    service = CategoryService(db)
    category = await service.get_by_id(category_id, restaurant.id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryRead.model_validate(category)


@router.put("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a category"""
    service = CategoryService(db)
    category = await service.update(category_id, restaurant.id, data)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryRead.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a category"""
    service = CategoryService(db)
    success = await service.delete(category_id, restaurant.id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")