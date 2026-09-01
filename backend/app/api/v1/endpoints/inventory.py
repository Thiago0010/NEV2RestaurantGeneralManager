from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydantic import BaseModel
from typing import Annotated, Optional, List

from app.api.deps import get_db, get_restaurant_from_user
from app.models import Restaurant, Product
from app.schemas import ProductRead
from app.services.crud import InventoryService, RecipeService

router = APIRouter(prefix="/inventory", tags=["inventory"])

class StockUpdateRequest(BaseModel):
    product_id: UUID
    quantity: float
    movement_type: str # 'IN', 'OUT', 'ADJUSTMENT'
    reason: Optional[str] = None

class RecipeItemRequest(BaseModel):
    ingredient_id: UUID
    quantity: float

class RecipeRequest(BaseModel):
    ingredients: List[RecipeItemRequest]

@router.post("/update", response_model=ProductRead)
async def update_stock(
    data: Annotated[StockUpdateRequest, Body()],
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Update product stock and log movement"""
    service = InventoryService(db)
    try:
        return await service.update_stock(
            product_id=data.product_id,
            restaurant_id=restaurant.id,
            quantity=data.quantity,
            movement_type=data.movement_type,
            reason=data.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/report", response_model=List[ProductRead])
async def get_stock_report(
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Get stock level for all products in the restaurant"""
    service = InventoryService(db)
    return await service.get_stock_report(restaurant.id)

@router.post("/products/{product_id}/recipe", response_model=ProductRead)
async def set_product_recipe(
    product_id: UUID,
    data: Annotated[RecipeRequest, Body()],
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Define the Bill of Materials (BOM) for a product"""
    service = RecipeService(db)
    ingredients = [item.model_dump() for item in data.ingredients]
    return await service.create_or_update_recipe(product_id, restaurant.id, ingredients)

@router.get("/products/{product_id}/recipe")
async def get_product_recipe(
    product_id: UUID,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the Bill of Materials (BOM) for a product"""
    service = RecipeService(db)
    return await service.get_recipe(product_id, restaurant.id)
