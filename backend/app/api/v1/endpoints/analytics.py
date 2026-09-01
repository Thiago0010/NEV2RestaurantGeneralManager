from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Dict, Any, List
from datetime import datetime
from uuid import UUID

from app.api.deps import get_db, get_restaurant_from_user
from app.models import Restaurant
from app.services.crud import FinancialService

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/revenue")
async def get_revenue(
    start_date: Annotated[str, Query(description="ISO date YYYY-MM-DD")],
    end_date: Annotated[str, Query(description="ISO date YYYY-MM-DD")],
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Get revenue stats for a specific period"""
    service = FinancialService(db)
    return await service.get_revenue_stats(
        restaurant_id=restaurant.id,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/top-products")
async def get_top_products(
    limit: int = 5,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the most sold products"""
    service = FinancialService(db)
    return await service.get_top_products(
        restaurant_id=restaurant.id,
        limit=limit
    )
