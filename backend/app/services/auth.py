from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models import User, Restaurant
from app.schemas import UserCreate, UserRole, RestaurantCreate
from app.core.security import get_password_hash, verify_password, create_access_token
from app.utils.format import slugify


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register_owner(
        self,
        email: str,
        password: str,
        full_name: str,
        restaurant_data: Optional[RestaurantCreate] = None
    ) -> tuple[User, Optional[Restaurant], str]:
        # Check if email exists
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        restaurant = None
        if restaurant_data:
            # Check if slug exists
            existing_slug = await self.db.execute(
                select(Restaurant).where(Restaurant.slug == restaurant_data.slug)
            )
            if existing_slug.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Slug already in use")
            
            # Create restaurant
            restaurant = Restaurant(**restaurant_data.model_dump())
            self.db.add(restaurant)
            await self.db.flush()
        
        # Create owner user
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=UserRole.OWNER,
            restaurant_id=restaurant.id if restaurant else None,
            is_active=True
        )
        self.db.add(user)
        await self.db.flush()
        
        # Create access token
        token = create_access_token(
            data={"sub": str(user.id), "restaurant_id": str(restaurant.id) if restaurant else None, "role": user.role.value}
        )
        
        return user, restaurant, token
    
    async def login(self, email: str, password: str) -> tuple[User, str]:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        
        # Update last login
        from app.utils.format import today_iso
        user.last_login = today_iso()
        
        token = create_access_token(
            data={"sub": str(user.id), "restaurant_id": str(user.restaurant_id) if user.restaurant_id else None, "role": user.role.value}
        )
        
        return user, token
    
    async def create_staff(
        self,
        restaurant_id: UUID,
        email: str,
        password: str,
        full_name: str,
        role: UserRole
    ) -> User:
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=role,
            restaurant_id=restaurant_id,
            is_active=True
        )
        self.db.add(user)
        await self.db.flush()
        return user
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> bool:
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        user.hashed_password = get_password_hash(new_password)
        await self.db.flush()
        return True