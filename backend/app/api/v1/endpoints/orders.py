from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List

from app.api.deps import get_db, get_current_active_user, get_restaurant_from_user, get_optional_user
from app.schemas import (
    OrderCreate, OrderUpdate, OrderRead, OrderSummaryRead,
    OrderItemCreate,
    PaginatedResponse
)
from app.services.crud import OrderService, TableService
from app.models import Restaurant, Table, OrderStatus, TableStatus
from app.api.v1.websockets.manager import manager
from app.core.config import settings

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new order (from waiter or customer)"""
    service = OrderService(db)
    
    # Verify table exists and is free/occupied
    table = await TableService(db).get_by_id(data.table_id, restaurant.id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    order = await service.create(data, restaurant.id, restaurant.service_tax_percent)
    
    # Broadcast update
    order_read = OrderRead.model_validate(order)
    await manager.broadcast_order_update(restaurant.id, order_read.model_dump(mode="json"))
    await manager.broadcast_table_update(restaurant.id, {
        "id": str(table.id),
        "number": table.number,
        "status": table.status.value,
        "current_order_id": str(table.current_order_id) if table.current_order_id else None
    })
    
    return order_read


@router.get("", response_model=PaginatedResponse)
async def list_orders(
    status: Optional[List[str]] = Query(None),
    table_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    created_date_gte: Optional[str] = Query(None, description="Filter orders created on or after this date (ISO format)"),
    created_date_lte: Optional[str] = Query(None, description="Filter orders created on or before this date (ISO format)"),
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """List orders"""
    service = OrderService(db)
    
    order_statuses = None
    if status:
        order_statuses = []
        for s in status:
            try:
                order_statuses.append(OrderStatus(s))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {s}")
    
    orders, total = await service.list(
        restaurant.id,
        status=order_statuses,
        table_id=table_id,
        created_date_gte=created_date_gte,
        created_date_lte=created_date_lte,
        page=page,
        page_size=page_size
    )
    
    return PaginatedResponse(
        items=[OrderRead.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/active", response_model=List[OrderSummaryRead])
async def get_active_orders(
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Get active orders (for kitchen/waiter)"""
    service = OrderService(db)
    orders, _ = await service.list(
        restaurant.id,
        status=[OrderStatus.RECEIVED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.DELIVERED],
        page_size=200
    )
    
    return [
        OrderSummaryRead(
            id=o.id,
            table_number=o.table_number,
            status=o.status,
            total=o.total,
            created_at=o.created_at,
            items_count=len(o.items)
        ) for o in orders
    ]


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: UUID,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Get an order by ID"""
    service = OrderService(db)
    order = await service.get_by_id(order_id, restaurant.id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderRead.model_validate(order)


@router.put("/{order_id}", response_model=OrderRead)
async def update_order(
    order_id: UUID,
    data: OrderUpdate,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an order (status, payment_method)"""
    service = OrderService(db)
    order = await service.update(order_id, restaurant.id, data)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order_read = OrderRead.model_validate(order)
    
    # Broadcast update
    await manager.broadcast_order_update(restaurant.id, order_read.model_dump(mode="json"))
    
    # If order closed, update table
    if data.status == OrderStatus.CLOSED and order.table_id:
        table = await TableService(db).get_by_id(order.table_id, restaurant.id)
        if table:
            await manager.broadcast_table_update(restaurant.id, {
                "id": str(table.id),
                "number": table.number,
                "status": table.status.value,
                "current_order_id": str(table.current_order_id) if table.current_order_id else None
            })
    
    # Also broadcast to kitchen if status changed
    if data.status:
        await manager.broadcast_kitchen_update(restaurant.id, order_read.model_dump(mode="json"))
    
    return order_read


@router.post("/{order_id}/items", response_model=OrderRead)
async def add_order_items(
    order_id: UUID,
    items: List[OrderItemCreate],
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Add items to an existing order"""
    service = OrderService(db)
    order = await service.add_items(order_id, restaurant.id, items, restaurant.service_tax_percent)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order_read = OrderRead.model_validate(order)
    
    # Broadcast update
    await manager.broadcast_order_update(restaurant.id, order_read.model_dump(mode="json"))
    await manager.broadcast_kitchen_update(restaurant.id, order_read.model_dump(mode="json"))
    
    return order_read


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order_item(
    item_id: UUID,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an order item"""
    service = OrderService(db)
    success = await service.delete_item(item_id, restaurant.id, restaurant.service_tax_percent)
    if not success:
        raise HTTPException(status_code=404, detail="Order item not found")
    
    # Note: Could broadcast update here if needed