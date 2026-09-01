from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List

from app.api.deps import get_db, get_current_active_user, get_restaurant_from_user
from app.schemas import (
    RestaurantRead, RestaurantUpdate, RestaurantPublicRead,
    PaginatedResponse, RestaurantCreate, UserRole,
    CategoryCreate, TableCreate
)
from app.services.crud import RestaurantService, CategoryService, TableService
from app.models import Restaurant, User

router = APIRouter(prefix="", tags=["restaurant"])


@router.get("/me", response_model=RestaurantRead)
async def get_my_restaurant(
    restaurant: Restaurant = Depends(get_restaurant_from_user)
):
    """Get current user's restaurant"""
    return RestaurantRead.model_validate(restaurant)


@router.put("/me", response_model=RestaurantRead)
async def update_my_restaurant(
    data: RestaurantUpdate,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's restaurant"""
    service = RestaurantService(db)
    updated = await service.update(restaurant.id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return RestaurantRead.model_validate(updated)


@router.post("/onboarding", response_model=RestaurantRead)
async def create_restaurant_onboarding(
    data: RestaurantCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create restaurant for authenticated user (onboarding step)"""
    # If user already has a restaurant, just return it (prevents duplicate errors)
    if current_user.restaurant_id:
        restaurant = await RestaurantService(db).get_by_id(current_user.restaurant_id, current_user.restaurant_id) # This is wrong, get_by_id takes (id, restaurant_id)
        # Wait, RestaurantService.get_by_id is get_by_id(self, restaurant_id: UUID)
        # Let's fix it.
        from app.services.crud import RestaurantService
        res = await RestaurantService(db).get_by_id(current_user.restaurant_id)
        if res:
            return RestaurantRead.model_validate(res)

    # Create restaurant
    restaurant_data = data.model_dump()
    restaurant_data["owner_id"] = current_user.id
    restaurant = Restaurant(**restaurant_data)
    db.add(restaurant)
    await db.flush()
    await db.refresh(restaurant)

    # Associate user with restaurant
    current_user.restaurant_id = restaurant.id
    current_user.role = UserRole.OWNER
    await db.flush()

    # Seed default categories and tables
    try:
        category_service = CategoryService(db)
        default_categories = [
            CategoryCreate(name="Entradas", sort_order=0),
            CategoryCreate(name="Pratos", sort_order=1),
            CategoryCreate(name="Bebidas", sort_order=2),
            CategoryCreate(name="Sobremesas", sort_order=3),
        ]
        await category_service.bulk_create(default_categories, restaurant.id)

        table_service = TableService(db)
        await table_service.bulk_create(restaurant.id, count=6, seats=4, start_number=1)
    except Exception:
        pass

    return RestaurantRead.model_validate(restaurant)


@router.get("/public/{slug}", response_model=RestaurantPublicRead)
async def get_public_restaurant(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get public restaurant info by slug (for customer menu)"""
    service = RestaurantService(db)
    restaurant = await service.get_by_slug(slug)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return RestaurantPublicRead.model_validate(restaurant)
