from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.redis_client import is_token_blocked
from app.models import User, Restaurant, PlanStatus, UserSession


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Check if token is blocked in Redis
    if await is_token_blocked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    jti: str = payload.get("jti")
    if user_id is None:
        raise credentials_exception

    # Check if session exists in UserSession table (enforce concurrent limit)
    if jti:
        session_result = await db.execute(select(UserSession).where(UserSession.token_jti == jti))
        if not session_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalidated by another login",
                headers={"WWW-Authenticate": "Bearer"},
            )

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    return current_user


async def get_restaurant_from_user(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Restaurant:
    if not current_user.restaurant_id:
        raise HTTPException(status_code=400, detail="User not associated with a restaurant")

    result = await db.execute(
        select(Restaurant).where(Restaurant.id == current_user.restaurant_id)
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    if restaurant.plan_status not in [PlanStatus.ACTIVE, PlanStatus.TRIALING]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Your subscription is inactive. Please renew your plan to continue."
        )

    return restaurant


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not token:
        return None
    
    try:
        payload = decode_access_token(token)
        if payload is None:
            return None
        
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()
        
        if user and user.is_active:
            return user
    except Exception:
        pass
    
    return None


def require_role(*allowed_roles: str):
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        role_value = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
        if role_value not in allowed_roles and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker