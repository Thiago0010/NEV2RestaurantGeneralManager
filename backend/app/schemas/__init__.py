from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import enum


class UserRole(str, enum.Enum):
    OWNER = "owner"
    MANAGER = "manager"
    WAITER = "waiter"
    KITCHEN = "kitchen"


class TableStatus(str, enum.Enum):
    FREE = "free"
    OCCUPIED = "occupied"
    WAITING = "waiting"
    PREPARING = "preparing"
    BILL_REQUESTED = "bill_requested"
    CLOSING = "closing"


class OrderStatus(str, enum.Enum):
    RECEIVED = "received"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERED = "delivered"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    PIX = "pix"
    CARD = "card"
    OTHER = "other"


class ServiceCallType(str, enum.Enum):
    HELP = "help"
    ORDER = "order"
    BILL = "bill"


class ServiceCallStatus(str, enum.Enum):
    PENDING = "pending"
    ASSUMED = "assumed"
    RESOLVED = "resolved"


# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserRead"


class TokenData(BaseModel):
    sub: Optional[str] = None
    restaurant_id: Optional[UUID] = None
    role: Optional[UserRole] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.OWNER
    restaurant_id: Optional[UUID] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    email: str
    full_name: Optional[str]
    role: UserRole
    restaurant_id: Optional[UUID]
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Restaurant schemas
class RestaurantBase(BaseModel):
    name: str
    description: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    currency: str = "R$"
    service_tax_percent: float = 10.0
    welcome_message: Optional[str] = None
    accent_color: str = "#e07a3c"
    logo_url: Optional[str] = None
    cover_image: Optional[str] = None
    slug: str


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    currency: Optional[str] = None
    service_tax_percent: Optional[float] = None
    welcome_message: Optional[str] = None
    accent_color: Optional[str] = None
    logo_url: Optional[str] = None
    cover_image: Optional[str] = None
    slug: Optional[str] = None


class RestaurantRead(RestaurantBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    # Billing / Mercado Pago fields. They live on the restaurant row but
    # the public schema deliberately doesn't expose them.
    plan_name: str
    plan_status: str
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    trial_end: Optional[datetime] = None
    mp_customer_id: Optional[str] = None
    mp_subscription_id: Optional[str] = None
    mp_payment_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RestaurantPublicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    currency: str
    service_tax_percent: float
    welcome_message: Optional[str]
    accent_color: str
    logo_url: Optional[str]
    cover_image: Optional[str]
    slug: str


# Category schemas
class CategoryBase(BaseModel):
    name: str
    slug: Optional[str] = None
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    restaurant_id: UUID
    created_at: datetime
    updated_at: datetime


# Product schemas
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category_id: Optional[UUID] = None
    image_url: Optional[str] = None
    is_available: bool = True
    featured: bool = False
    stock_quantity: float = 0.0


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[UUID] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None
    featured: Optional[bool] = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    restaurant_id: UUID
    created_at: datetime
    updated_at: datetime


# Table schemas
class TableBase(BaseModel):
    number: str
    seats: int = 4


class TableCreate(TableBase):
    qty: int = 1


class TableUpdate(BaseModel):
    number: Optional[str] = None
    seats: Optional[int] = None


class TableRead(TableBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    restaurant_id: UUID
    status: TableStatus
    current_order_id: Optional[UUID]
    opened_at: Optional[datetime]
    qr_token: str
    qr_code_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# Order schemas
class OrderItemCreate(BaseModel):
    # product_id is nullable on the OrderItem model (custom/misc items from the
    # public menu may not reference a Product row), so the schema accepts it as
    # optional too. Empty strings (e.g. from a form whose field was blank) are
    # normalized to None before validation to avoid a spurious 422.
    product_id: Optional[UUID] = None
    product_name: str
    quantity: int = 1
    unit_price: float
    notes: Optional[str] = None

    @field_validator("product_id", mode="before")
    @classmethod
    def _empty_uuid_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v


class OrderCreate(BaseModel):
    # table_id is nullable on the Order model as well (e.g. takeaway without a
    # seated table); accept empty strings as None to avoid 422s from the front.
    table_id: Optional[UUID] = None
    table_number: str
    items: List[OrderItemCreate]

    @field_validator("table_id", mode="before")
    @classmethod
    def _empty_uuid_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    payment_method: Optional[PaymentMethod] = None


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    product_id: Optional[UUID]
    product_name: str
    quantity: int
    unit_price: float
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    restaurant_id: UUID
    table_id: Optional[UUID]
    table_number: str
    status: OrderStatus
    subtotal: float
    service_tax: float
    total: float
    payment_method: Optional[PaymentMethod]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    items: List[OrderItemRead] = []


class OrderSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    table_number: str
    status: OrderStatus
    total: float
    created_at: datetime
    items_count: int = 0


# Employee schemas
class EmployeeBase(BaseModel):
    name: str
    role: UserRole = UserRole.WAITER
    phone: Optional[str] = None
    is_active: bool = True


class EmployeeCreate(EmployeeBase):
    hire_date: Optional[datetime] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    restaurant_id: UUID
    hire_date: datetime
    created_at: datetime
    updated_at: datetime


# ServiceCall schemas
class ServiceCallCreate(BaseModel):
    table_id: UUID
    table_number: str
    type: ServiceCallType


class ServiceCallUpdate(BaseModel):
    status: ServiceCallStatus


class ServiceCallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    restaurant_id: UUID
    table_id: UUID
    table_number: str
    type: ServiceCallType
    status: ServiceCallStatus
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]


# Pagination
class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    page_size: int
    total_pages: int


# WebSocket messages
class WSMessage(BaseModel):
    type: str
    payload: dict


# QR Code
class QRCodeResponse(BaseModel):
    table_id: UUID
    table_number: str
    qr_token: str
    qr_code_url: str
    public_url: str


# Import billing schemas
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
    PlanInfo,
    BillingStatus,
    PlanResponse,
    AdminMRRResponse,
    AdminRevenueResponse,
    AdminChurnResponse,
    AdminByPlanResponse,
    BillingEventRead,
)

__all__ = [
    "UserRole",
    "TableStatus",
    "OrderStatus",
    "PaymentMethod",
    "ServiceCallType",
    "ServiceCallStatus",
    "Token",
    "TokenData",
    "UserCreate",
    "UserUpdate",
    "UserRead",
    "LoginRequest",
    "RestaurantBase",
    "RestaurantCreate",
    "RestaurantUpdate",
    "RestaurantRead",
    "RestaurantPublicRead",
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryRead",
    "ProductBase",
    "ProductCreate",
    "ProductUpdate",
    "ProductRead",
    "TableBase",
    "TableCreate",
    "TableUpdate",
    "TableRead",
    "OrderItemCreate",
    "OrderCreate",
    "OrderUpdate",
    "OrderItemRead",
    "OrderRead",
    "OrderSummaryRead",
    "EmployeeBase",
    "EmployeeCreate",
    "EmployeeUpdate",
    "EmployeeRead",
    "ServiceCallCreate",
    "ServiceCallUpdate",
    "ServiceCallRead",
    "PaginatedResponse",
    "WSMessage",
    "QRCodeResponse",
    "CheckoutRequest",
    "CheckoutResponse",
    "PortalResponse",
    "PlanInfo",
    "BillingStatus",
    "PlanResponse",
    "AdminMRRResponse",
    "AdminRevenueResponse",
    "AdminChurnResponse",
    "AdminByPlanResponse",
    "BillingEventRead",
]