from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.api.deps import get_db
from app.api.v1.websockets.manager import manager, websocket_endpoint, public_websocket_endpoint
from app.core.security import decode_access_token
from app.models import User
from sqlalchemy import select


router = APIRouter(prefix="/ws", tags=["websockets"])


async def get_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
    """Get user from JWT token"""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user and user.is_active:
        return user
    return None


@router.websocket("/restaurant/{restaurant_id}")
async def websocket_restaurant(
    websocket: WebSocket,
    restaurant_id: UUID,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket for authenticated users (admin/waiter/kitchen)"""
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    if user.restaurant_id != restaurant_id and not user.is_superuser:
        await websocket.close(code=4003, reason="Not authorized for this restaurant")
        return
    
    await websocket_endpoint(websocket, restaurant_id, user.id)


@router.websocket("/public/restaurant/{restaurant_id}/table/{table_id}")
async def websocket_public_table(
    websocket: WebSocket,
    restaurant_id: UUID,
    table_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket for public customer menu (no auth)"""
    # Verify table exists and belongs to restaurant
    from app.services.crud import TableService
    table = await TableService(db).get_by_id(table_id, restaurant_id)
    if not table:
        await websocket.close(code=4004, reason="Table not found")
        return
    
    await public_websocket_endpoint(websocket, restaurant_id, table_id)