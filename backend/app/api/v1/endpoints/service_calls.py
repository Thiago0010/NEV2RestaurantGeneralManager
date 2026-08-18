from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.api.deps import get_db, get_current_active_user, get_restaurant_from_user
from app.schemas import (
    ServiceCallCreate, ServiceCallUpdate, ServiceCallRead,
    PaginatedResponse
)
from app.services.crud import ServiceCallService
from app.models import Restaurant, ServiceCallStatus
from app.api.v1.websockets.manager import manager

router = APIRouter(prefix="/service-calls", tags=["service-calls"])


@router.post("", response_model=ServiceCallRead, status_code=status.HTTP_201_CREATED)
async def create_service_call(
    data: ServiceCallCreate,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new service call (from customer menu)"""
    service = ServiceCallService(db)
    call = await service.create(data, restaurant.id)
    
    call_read = ServiceCallRead.model_validate(call)
    
    # Broadcast to waiters
    await manager.broadcast_service_call(restaurant.id, call_read.model_dump(mode="json"))
    
    return call_read


@router.get("", response_model=PaginatedResponse)
async def list_service_calls(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=500),
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """List service calls"""
    service = ServiceCallService(db)
    
    call_status = None
    if status:
        try:
            call_status = ServiceCallStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    calls, total = await service.list(restaurant.id, call_status, page, page_size)
    
    return PaginatedResponse(
        items=[ServiceCallRead.model_validate(c) for c in calls],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/pending", response_model=list[ServiceCallRead])
async def get_pending_service_calls(
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Get pending service calls (for waiter)"""
    service = ServiceCallService(db)
    calls, _ = await service.list(restaurant.id, ServiceCallStatus.PENDING, page_size=200)
    return [ServiceCallRead.model_validate(c) for c in calls]


@router.put("/{call_id}", response_model=ServiceCallRead)
async def update_service_call(
    call_id: UUID,
    data: ServiceCallUpdate,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a service call status"""
    service = ServiceCallService(db)
    call = await service.update_status(call_id, restaurant.id, data.status)
    if not call:
        raise HTTPException(status_code=404, detail="Service call not found")
    
    call_read = ServiceCallRead.model_validate(call)
    
    # Broadcast update
    await manager.broadcast_service_call(restaurant.id, call_read.model_dump(mode="json"))
    
    return call_read