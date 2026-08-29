from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List

from app.api.deps import get_db, get_optional_user
from app.schemas import (
    RestaurantPublicRead,
    CategoryRead,
    ProductRead,
    TableRead,
    OrderRead,
    OrderCreate,
    OrderItemCreate,
    ServiceCallCreate,
    QRCodeResponse
)
from app.services.crud import (
    RestaurantService, CategoryService, ProductService,
    TableService, OrderService
)
from app.models import Restaurant, Table, OrderStatus
from app.api.v1.websockets.manager import manager
from app.core.config import settings

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/restaurant/{slug}", response_model=RestaurantPublicRead)
async def get_restaurant_public(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get public restaurant info by slug"""
    service = RestaurantService(db)
    restaurant = await service.get_by_slug(slug)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return RestaurantPublicRead.model_validate(restaurant)


@router.get("/restaurant/qr/{qr_token}", response_model=dict)
async def get_restaurant_by_qr(
    qr_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Get restaurant and table info by QR token"""
    table = await TableService(db).get_by_qr_token(qr_token)
    if not table:
        raise HTTPException(status_code=404, detail="Invalid QR code")
    
    restaurant_service = RestaurantService(db)
    restaurant = await restaurant_service.get_by_id(table.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    return {
        "restaurant": RestaurantPublicRead.model_validate(restaurant),
        "table": {
            "id": str(table.id),
            "number": table.number,
            "seats": table.seats,
            "qr_token": table.qr_token
        }
    }


@router.get("/restaurant/{restaurant_id}/categories", response_model=List[CategoryRead])
async def get_public_categories(
    restaurant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get public categories for a restaurant"""
    service = CategoryService(db)
    categories, _ = await service.list(restaurant_id, page_size=500)
    return [CategoryRead.model_validate(c) for c in categories]


@router.get("/restaurant/{restaurant_id}/products", response_model=List[ProductRead])
async def get_public_products(
    restaurant_id: UUID,
    category_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get public products for a restaurant (available only)"""
    service = ProductService(db)
    products, _ = await service.list(
        restaurant_id,
        category_id=category_id,
        available_only=True,
        page_size=1000
    )
    return [ProductRead.model_validate(p) for p in products]


@router.get("/restaurant/{restaurant_id}/tables/{table_number}", response_model=TableRead)
async def get_public_table(
    restaurant_id: UUID,
    table_number: str,
    db: AsyncSession = Depends(get_db)
):
    """Get public table info by number"""
    from sqlalchemy import select
    result = await db.execute(
        select(Table).where(
            Table.restaurant_id == restaurant_id,
            Table.number == table_number
        )
    )
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    tr = TableRead.model_validate(table)
    tr.qr_code_url = f"{settings.BASE_URL.rstrip('/')}/r/qr/{table.qr_token}"
    return tr


@router.get("/restaurant/{restaurant_id}/orders/active", response_model=Optional[OrderRead])
async def get_active_order_for_table(
    restaurant_id: UUID,
    table_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the still-tracked order for a table (for customer tracking).

    Only ``received``/``preparing``/``ready`` are considered "in flight" from
    the customer's point of view — once the order is ``delivered`` the tracking
    panel has nothing left to show, and a brand-new visit to the menu must
    start with no active order (so the customer can place another one).
    Returning the stale ``delivered`` order here is what made the tracking
    timeline render every step as "done" on the next visit.

    We additionally anchor the lookup to the table's ``current_order_id`` so
    a previous-but-detached order (e.g. an order the kitchen handed out and
    forgot to close) doesn't reappear on the next visit.
    """
    from app.models import Table
    table_row = await db.execute(
        select(Table).where(
            Table.restaurant_id == restaurant_id,
            Table.id == table_id,
        )
    )
    table = table_row.scalar_one_or_none()
    if not table or not table.current_order_id:
        return None

    service = OrderService(db)
    active = await service.get_by_id(table.current_order_id, restaurant_id)
    if not active or active.status not in (
        OrderStatus.RECEIVED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
    ):
        return None
    return OrderRead.model_validate(active)


@router.post("/restaurant/{restaurant_id}/orders", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_public_order(
    restaurant_id: UUID,
    data: OrderCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create order from customer menu (no auth)"""
    # Verify restaurant exists
    restaurant_service = RestaurantService(db)
    restaurant = await restaurant_service.get_by_id(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    service = OrderService(db)
    try:
        order = await service.create(data, restaurant_id, restaurant.service_tax_percent)
    except ValueError as e:
        # Service raised because the table already has an open order. The
        # customer flow should have used addItems; surface 409 so the
        # client can recover (its public /orders/active call will return
        # the existing order and it can re-send the cart against that id).
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    
    # Broadcast update
    order_read = OrderRead.model_validate(order)
    await manager.broadcast_order_update(restaurant_id, order_read.model_dump(mode="json"))
    await manager.broadcast_table_update(restaurant_id, {
        "id": str(data.table_id),
        "number": data.table_number,
        "status": "occupied",
        "current_order_id": str(order.id)
    })
    
    return order_read


@router.post("/restaurant/{restaurant_id}/orders/{order_id}/items", response_model=OrderRead)
async def add_items_to_public_order(
    restaurant_id: UUID,
    order_id: UUID,
    items: List[OrderItemCreate],
    db: AsyncSession = Depends(get_db)
):
    """Add items to existing order from customer menu"""
    restaurant_service = RestaurantService(db)
    restaurant = await restaurant_service.get_by_id(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    service = OrderService(db)
    order = await service.add_items(order_id, restaurant_id, items, restaurant.service_tax_percent)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order_read = OrderRead.model_validate(order)
    
    # Broadcast update
    await manager.broadcast_order_update(restaurant_id, order_read.model_dump(mode="json"))
    await manager.broadcast_kitchen_update(restaurant_id, order_read.model_dump(mode="json"))
    
    return order_read


@router.post("/restaurant/{restaurant_id}/service-calls", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_public_service_call(
    restaurant_id: UUID,
    data: ServiceCallCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create service call from customer menu (no auth)"""
    restaurant_service = RestaurantService(db)
    restaurant = await restaurant_service.get_by_id(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    from app.services.crud import ServiceCallService
    service = ServiceCallService(db)
    call = await service.create(data, restaurant_id)
    
    call_read = call
    
    # Broadcast to waiters
    await manager.broadcast_service_call(restaurant_id, {
        "id": str(call.id),
        "table_id": str(call.table_id),
        "table_number": call.table_number,
        "type": call.type.value,
        "status": call.status.value,
        "created_at": call.created_at.isoformat()
    })
    
    return {"success": True, "call_id": str(call.id)}