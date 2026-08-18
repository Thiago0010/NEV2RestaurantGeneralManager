from pydantic import BaseModel, EmailStr, ConfigDict
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
    available: bool = True
    featured: bool = False


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[UUID] = None
    image_url: Optional[str] = None
    available: Optional[bool] = None
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
    qr_code_url: str
    created_at: datetime
    updated_at: datetime


# Order schemas
class OrderItemCreate(BaseModel):
    product_id: UUID
    product_name: str
    quantity: int = 1
    unit_price: float
    notes: Optional[str] = None


class OrderCreate(BaseModel):
    table_id: UUID
    table_number: str
    items: List[OrderItemCreate]


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
    active: bool = True


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    phone: Optional[str] = None
    active: Optional[bool] = None


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    restaurant_id: UUID
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