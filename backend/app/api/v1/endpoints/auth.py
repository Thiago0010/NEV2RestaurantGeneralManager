from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from typing import Annotated, Optional
from datetime import datetime, timedelta, timezone
import secrets

from app.api.deps import get_db, get_current_active_user, get_restaurant_from_user, oauth2_scheme, require_role
from app.schemas import (
    LoginRequest, Token, UserRead, UserCreate, RestaurantCreate,
    RestaurantRead, RestaurantUpdate, UserRole
)
from app.services.auth import AuthService
from app.services.crud import RestaurantService
from app.models import User, Restaurant
from app.core.config import settings
from app.core.rate_limit import stricter_rate_limit
from app.core.security import get_password_hash, verify_password
from app.utils.email import send_email
from app.core.redis_client import block_token

# Map Portuguese role names to UserRole enum values
ROLE_MAPPING = {
    "gerente": "manager",
    "cozinha": "kitchen",
    "garçom": "waiter",
    "garcom": "waiter",
    "dono": "owner",
}

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
        expected_secret = getattr(settings, 'SECRET_KEY_REGISTER', None)
        if not expected_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Configuração do servidor ausente: SECRET_KEY_REGISTER não definida."
            )
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
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password"""
    auth_service = AuthService(db)
    user, token = await auth_service.login(credentials.email, credentials.password, request)

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
    current_user: User = Depends(require_role("owner", "manager")),
    db: AsyncSession = Depends(get_db)
):
    """Create a staff user (requires owner/manager)"""
    from app.schemas import UserRole

    if not current_user.restaurant_id:
        raise HTTPException(status_code=400, detail="No restaurant associated")

    try:
        # Normalize role if provided in Portuguese
        role_str = data.role.lower().strip()
        normalized_role = ROLE_MAPPING.get(role_str, role_str)
        staff_role = UserRole(normalized_role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {data.role}")

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
    """Update current user profile"""
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
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user:
        # Generate secure random token
        random_token = secrets.token_urlsafe(32)

        # Store hashed token and expiration (30 minutes)
        user.reset_token_hash = get_password_hash(random_token)
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=30)

        await db.commit()

        # Construct reset link with composite token: "userId:randomToken"
        composite_token = f"{user.id}:{random_token}"
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={composite_token}"
        subject = "Redefinição de Senha"

        # Plain text fallback
        body = f"[v2.0] Você solicitou a redefinição de sua senha. Por favor, clique no link abaixo para definir uma nova senha:\n\n{reset_link}\n\nEste link expira em 30 minutos."

        # Professional HTML Template based on NEV design
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="margin: 0; padding: 0; background-color: #1E1E1E; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #1E1E1E; padding: 40px 20px;">
                <tr>
                    <td align="center">
                        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; background-color: #332E28; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                            <!-- Header / Accent Bar -->
                            <tr>
                                <td height="8" style="background-color: #F2B765;"></td>
                            </tr>

                            <!-- Content Area -->
                            <tr>
                                <td style="padding: 40px 30px;">
                                    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #5B5147; border-radius: 8px; padding: 30px;">
                                        <tr>
                                            <td align="center" style="color: #FFE397; font-size: 24px; font-weight: bold; padding-bottom: 20px;">
                                                Redefinição de Senha
                                            </td>
                                        </tr>
                                        <tr>
                                            <td align="center" style="color: #FFFFFF; font-size: 16px; line-height: 1.6; padding-bottom: 30px;">
                                                Olá!<br><br>
                                                Recebemos uma solicitação para redefinir a senha da sua conta.
                                                Para prosseguir, clique no botão abaixo.
                                            </td>
                                        </tr>
                                        <tr>
                                            <td align="center">
                                                <a href="{reset_link}" style="background-color: #438FCD; color: #FFFFFF; padding: 15px 30px; text-decoration: none; font-weight: bold; border-radius: 8px; display: inline-block; font-size: 16px; transition: background-color 0.3s ease;">
                                                    Redefinir Minha Senha
                                                </a>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td align="center" style="color: #D1C7B7; font-size: 14px; line-height: 1.6; padding-top: 30px;">
                                                Este link é válido por <strong>30 minutos</strong>.<br>
                                                Se você não solicitou isso, pode ignorar este e-mail com segurança.
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>

                            <!-- Footer -->
                            <tr>
                                <td align="center" style="padding: 0 30px 40px 30px; color: #8A7E72; font-size: 12px; text-align: center;">
                                    &copy; {datetime.now().year} Restaurant Manager. Todos os direitos reservados.
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        try:
            await send_email(to=user.email, subject=subject, body=body, html_body=html_body)
        except Exception as e:
            # Log the error so we can debug it, but don't reveal details to the client
            import logging
            logging.error(f"Email delivery failed for {user.email}: {e}")

    return {"message": "If an account exists, a reset link has been sent."}


@router.post("/reset-password", dependencies=[Depends(stricter_rate_limit)])
async def reset_password(
    data: Annotated[ResetPasswordRequest, Body()],
    db: AsyncSession = Depends(get_db)
):
    """Reset password using a composite token (userId:randomToken)"""
    try:
        # Split composite token
        user_id_str, random_token = data.token.split(":", 1)
        user_id = UUID(user_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token format"
        )

    # Fetch specific user by ID - avoids iterating over all tokens (DoS prevention)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )

    # Verify token hash and expiration
    if not user.reset_token_hash or not verify_password(random_token, user.reset_token_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )

    # Ensure we are comparing offset-aware datetimes
    expires_at = user.reset_token_expires
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if not expires_at or expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token has expired"
        )

    # Update password and clear reset fields
    user.hashed_password = get_password_hash(data.new_password)
    user.reset_token_hash = None
    user.reset_token_expires = None

    await db.commit()

    return {"message": "Password has been reset successfully"}
