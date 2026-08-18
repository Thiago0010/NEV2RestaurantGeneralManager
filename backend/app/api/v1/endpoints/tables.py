from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List

from app.api.deps import get_db, get_current_active_user, get_restaurant_from_user
from app.schemas import (
    TableCreate, TableUpdate, TableRead, QRCodeResponse,
    PaginatedResponse
)
from app.services.crud import TableService
from app.models import Restaurant
from app.core.config import settings

router = APIRouter(prefix="/tables", tags=["tables"])


@router.post("", response_model=List[TableRead], status_code=status.HTTP_201_CREATED)
async def create_tables(
    data: TableCreate,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Create one or more tables"""
    service = TableService(db)
    tables = await service.create(data, restaurant.id)
    return [TableRead.model_validate(t) for t in tables]


@router.get("", response_model=PaginatedResponse)
async def list_tables(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(500, ge=1, le=500),
    include_qr: bool = Query(False),  # NOVO: opcional
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """List all tables - QR codes são gerados sob demanda"""
    service = TableService(db)
    
    table_status = None
    if status:
        from app.schemas import TableStatus
        try:
            table_status = TableStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    tables, total = await service.list(restaurant.id, table_status, page, page_size)
    
    table_reads = []
    for t in tables:
        tr = TableRead.model_validate(t)
        # SÓ gera QR code URL se solicitado
        if include_qr:
            tr.qr_code_url = f"{settings.BASE_URL.rstrip('/')}/r/qr/{t.qr_token}"
        table_reads.append(tr)
    
    return PaginatedResponse(
        items=table_reads,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/{table_id}", response_model=TableRead)
async def get_table(
    table_id: UUID,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a table by ID"""
    service = TableService(db)
    table = await service.get_by_id(table_id, restaurant.id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    tr = TableRead.model_validate(table)
    tr.qr_code_url = f"{settings.BASE_URL.rstrip('/')}/r/qr/{table.qr_token}"
    return tr


@router.get("/{table_id}/qr", response_model=QRCodeResponse)
async def get_table_qr(
    table_id: UUID,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Get QR code for a table"""
    service = TableService(db)
    qr_data = await service.get_qr_code(table_id, restaurant.id, settings.BASE_URL)
    if not qr_data:
        raise HTTPException(status_code=404, detail="Table not found")
    return QRCodeResponse(**qr_data)


@router.get("/qr/all", response_model=List[QRCodeResponse])
async def get_all_qr_codes(
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Get QR codes for all tables"""
    service = TableService(db)
    tables, _ = await service.list(restaurant.id, page_size=500)
    
    results = []
    for table in tables:
        qr_data = await service.get_qr_code(table.id, restaurant.id, settings.BASE_URL)
        if qr_data:
            results.append(QRCodeResponse(**qr_data))
    
    return results


@router.put("/{table_id}", response_model=TableRead)
async def update_table(
    table_id: UUID,
    data: TableUpdate,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a table"""
    service = TableService(db)
    table = await service.update(table_id, restaurant.id, data)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    tr = TableRead.model_validate(table)
    tr.qr_code_url = f"{settings.BASE_URL.rstrip('/')}/r/qr/{table.qr_token}"
    return tr


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    table_id: UUID,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a table"""
    service = TableService(db)
    success = await service.delete(table_id, restaurant.id)
    if not success:
        raise HTTPException(status_code=404, detail="Table not found")