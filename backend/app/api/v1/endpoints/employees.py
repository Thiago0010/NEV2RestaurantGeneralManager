from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
import secrets
import re

from app.api.deps import get_db, get_current_active_user, get_restaurant_from_user
from app.schemas import (
    EmployeeCreate, EmployeeUpdate, EmployeeRead,
    PaginatedResponse
)
from app.services.crud import EmployeeService
from app.models import Restaurant, User, UserRole
from app.core.security import get_password_hash

router = APIRouter(prefix="/employees", tags=["employees"])


def _slugify_for_email(name: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", ".", name.strip().lower()).strip(".")
    return base or "employee"


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new employee.

    The frontend only sends name/role/phone/is_active, so we synthesize a
    backing ``User`` row (random email + password) to satisfy the NOT NULL
    FK on ``employees.user_id``. The employee gets a real login later when
    the owner promotes them and resets the password.
    """
    service = EmployeeService(db)

    slug = _slugify_for_email(data.name)
    placeholder_email = (
        f"{slug}.{secrets.token_hex(4)}@employees.{restaurant.slug}.local"
    )
    random_password = secrets.token_urlsafe(24)
    user = User(
        email=placeholder_email,
        hashed_password=get_password_hash(random_password),
        full_name=data.name,
        is_active=data.is_active,
        role=data.role,
        restaurant_id=restaurant.id,
    )
    db.add(user)
    await db.flush()

    employee = await service.create(data, restaurant.id, user_id=user.id)
    await db.refresh(employee)
    return EmployeeRead.model_validate(employee)


@router.get("", response_model=PaginatedResponse)
async def list_employees(
    active_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(500, ge=1, le=500),
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """List all employees"""
    service = EmployeeService(db)
    employees, total = await service.list(restaurant.id, active_only, page, page_size)
    
    return PaginatedResponse(
        items=[EmployeeRead.model_validate(e) for e in employees],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: UUID,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Get an employee by ID"""
    service = EmployeeService(db)
    employee = await service.get_by_id(employee_id, restaurant.id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return EmployeeRead.model_validate(employee)


@router.put("/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: UUID,
    data: EmployeeUpdate,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an employee"""
    service = EmployeeService(db)
    employee = await service.update(employee_id, restaurant.id, data)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return EmployeeRead.model_validate(employee)


@router.patch("/{employee_id}/toggle-active", response_model=EmployeeRead)
async def toggle_employee_active(
    employee_id: UUID,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle employee active status"""
    service = EmployeeService(db)
    employee = await service.toggle_active(employee_id, restaurant.id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return EmployeeRead.model_validate(employee)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: UUID,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an employee"""
    service = EmployeeService(db)
    success = await service.delete(employee_id, restaurant.id)
    if not success:
        raise HTTPException(status_code=404, detail="Employee not found")