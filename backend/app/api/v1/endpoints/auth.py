from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from typing import Annotated, Optional

from app.api.deps import get_db, get_current_active_user, get_restaurant_from_user
from app.schemas import (
    LoginRequest, Token, UserRead, UserCreate, RestaurantCreate,
    RestaurantRead, RestaurantUpdate, UserRole
)
from app.services.auth import AuthService
from app.services.crud import RestaurantService
from app.models import User, Restaurant
from app.core.config import settings
from app.core.rate_limit import stricter_rate_limit

router = APIRouter(tags=["auth"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    restaurant_name: Optional[str] = None
    restaurant_slug: Optional[str] = None
    secret_key: Optional[str] = None


class CreateStaffRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str


class UpdateMeRequest(BaseModel):
    restaurant_id: Optional[str] = None
    staff_role: Optional[str] = None
    full_name: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register", response_model=Token, dependencies=[Depends(stricter_rate_limit)])
async def register(
    data: Annotated[RegisterRequest, Body()],
    db: AsyncSession = Depends(get_db)
):
    """Register a new restaurant owner"""
    # Validate secret key from env (only if restaurant data provided)
    if data.restaurant_name or data.restaurant_slug:
        expected_secret = settings.SECRET_KEY_REGISTER if hasattr(settings, 'SECRET_KEY_REGISTER') else "123"
        if data.secret_key != expected_secret:
            raise HTTPException(status_code=403, detail="Chave secreta inválida")
    
    auth_service = AuthService(db)
    
    restaurant_data = None
    if data.restaurant_name and data.restaurant_slug:
        restaurant_data = RestaurantCreate(
            name=data.restaurant_name,
            slug=data.restaurant_slug,
            currency="R$",
            service_tax_percent=10.0,
            accent_color="#e07a3c"
        )
    
    user, restaurant, token = await auth_service.register_owner(
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        restaurant_data=restaurant_data
    )
    
    return Token(
        access_token=token,
        user=UserRead.model_validate(user)
    )


@router.post("/login", response_model=Token, dependencies=[Depends(stricter_rate_limit)])
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password"""
    auth_service = AuthService(db)
    user, token = await auth_service.login(credentials.email, credentials.password)
    
    return Token(
        access_token=token,
        user=UserRead.model_validate(user)
    )


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info"""
    return UserRead.model_validate(current_user)


@router.post("/staff", response_model=UserRead)
async def create_staff(
    data: Annotated[CreateStaffRequest, Body()],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a staff user (requires owner/manager)"""
    from app.schemas import UserRole

    # Check permission
    if current_user.role not in [UserRole.OWNER, UserRole.MANAGER] and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    if not current_user.restaurant_id:
        raise HTTPException(status_code=400, detail="No restaurant associated")

    try:
        staff_role = UserRole(data.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    auth_service = AuthService(db)
    user = await auth_service.create_staff(
        restaurant_id=current_user.restaurant_id,
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        role=staff_role
    )

    return UserRead.model_validate(user)


@router.put("/me/password", dependencies=[Depends(stricter_rate_limit)])
async def change_password(
    data: Annotated[ChangePasswordRequest, Body()],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Change current user's password"""
    auth_service = AuthService(db)
    await auth_service.change_password(current_user.id, data.current_password, data.new_password)
    return {"message": "Password changed successfully"}


@router.put("/me", response_model=UserRead)
async def update_me(
    data: Annotated[UpdateMeRequest, Body()],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile (restaurant_id, role, name)"""
    if data.restaurant_id:
        from uuid import UUID
        try:
            current_user.restaurant_id = UUID(data.restaurant_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid restaurant_id (must be UUID)")
    if data.staff_role:
        from app.schemas import UserRole
        try:
            current_user.role = UserRole(data.staff_role)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid staff_role")
    if data.full_name:
        current_user.full_name = data.full_name

    await db.flush()
    return UserRead.model_validate(current_user)


@router.post("/forgot-password", dependencies=[Depends(stricter_rate_limit)])
async def forgot_password(
    data: Annotated[ForgotPasswordRequest, Body()],
    db: AsyncSession = Depends(get_db)
):
    """Request a password reset (always returns success to avoid leaking which emails are registered)"""
    # Stub: in production this would email a token. We only acknowledge.
    return {"message": "If an account exists, a reset link has been sent."}


@router.post("/reset-password", dependencies=[Depends(stricter_rate_limit)])
async def reset_password(
    data: Annotated[ResetPasswordRequest, Body()],
    db: AsyncSession = Depends(get_db)
):
    """Reset password using a previously issued token (stub for now)"""
    # Stub: token validation not implemented yet
    raise HTTPException(status_code=501, detail="Password reset via email is not enabled in this build.")