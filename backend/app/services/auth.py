from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException, status, Request

from app.models import User, Restaurant, AuditLog, UserSession
from app.schemas import UserCreate, UserRole, RestaurantCreate
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from app.utils.format import slugify
from app.services.crud import CategoryService, TableService, RestaurantService


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
            # Create the owner user first WITHOUT a restaurant_id
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name=full_name,
                role=UserRole.OWNER,
                restaurant_id=None,
                is_active=True,
            )
            self.db.add(user)
            await self.db.flush()

            # Use RestaurantService to create the restaurant (handles unique slug)
            restaurant_service = RestaurantService(self.db)
            restaurant = await restaurant_service.create(restaurant_data, user.id)

            # Backfill the user's restaurant_id
            user.restaurant_id = restaurant.id
            await self.db.flush()

            # Seed default categories and tables
            try:
                category_service = CategoryService(self.db)
                default_categories = [
                    {"name": "Entradas", "sort_order": 0},
                    {"name": "Pratos", "sort_order": 1},
                    {"name": "Bebidas", "sort_order": 2},
                    {"name": "Sobremesas", "sort_order": 3},
                ]
                # We use bulk_create but need to pass RestaurantCreate items or just call it
                # Let's look at CategoryService.bulk_create: it takes List[CategoryCreate]
                from app.schemas import CategoryCreate
                cat_items = [CategoryCreate(**c) for c in default_categories]
                await category_service.bulk_create(cat_items, restaurant.id)

                table_service = TableService(self.db)
                await table_service.bulk_create(restaurant.id, count=6, seats=4, start_number=1)
            except Exception:
                # Seed failure shouldn't block registration
                pass
        else:
            # No restaurant requested — register the user with no FK target.
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name=full_name,
                role=UserRole.OWNER,
                restaurant_id=None,
                is_active=True,
            )
            self.db.add(user)
            await self.db.flush()

        # Create access token
        token = create_access_token(
            data={"sub": str(user.id), "restaurant_id": str(restaurant.id) if restaurant else None, "role": user.role.value}
        )

        return user, restaurant, token
    
    async def login(self, email: str, password: str, request: Request) -> tuple[User, str]:
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

        # 1. Audit Log
        audit = AuditLog(
            user_id=user.id,
            restaurant_id=user.restaurant_id if user.restaurant_id else (await self.db.execute(select(Restaurant).where(Restaurant.owner_id == user.id))).scalar_one_or_none().id,
            action="LOGIN",
            details=f"Login successful via {request.client.host}",
            ip_address=request.client.host,
            device=request.headers.get("user-agent"),
        )
        self.db.add(audit)

        # 2. Handle Concurrent Sessions
        # We first generate the token and extract the JTI (which we added in security.py)
        from jose import jwt
        token = create_access_token(
            data={"sub": str(user.id), "restaurant_id": str(user.restaurant_id) if user.restaurant_id else None, "role": user.role.value}
        )
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")

        # Check current active sessions
        sessions_result = await self.db.execute(select(UserSession).where(UserSession.user_id == user.id))
        active_sessions = sessions_result.scalars().all()

        if len(active_sessions) >= settings.MAX_CONCURRENT_SESSIONS:
            # Remove oldest session
            oldest = min(active_sessions, key=lambda s: s.created_at)
            await self.db.delete(oldest)

        # Create new session
        new_session = UserSession(
            user_id=user.id,
            token_jti=jti,
            ip_address=request.client.host,
            device=request.headers.get("user-agent"),
        )
        self.db.add(new_session)

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