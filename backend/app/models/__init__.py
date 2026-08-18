from sqlalchemy import Column, String, Text, Boolean, Integer, Numeric, DateTime, ForeignKey, Enum as SQLEnum, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_mixin
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base


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


class Restaurant(Base):
    __tablename__ = "restaurants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    currency = Column(String(10), default="R$")
    service_tax_percent = Column(Numeric(5, 2), default=10.00)
    welcome_message = Column(Text, nullable=True)
    accent_color = Column(String(7), default="#e07a3c")
    logo_url = Column(String(500), nullable=True)
    cover_image = Column(String(500), nullable=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="restaurant", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="restaurant", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="restaurant", cascade="all, delete-orphan")
    tables = relationship("Table", back_populates="restaurant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="restaurant", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="restaurant", cascade="all, delete-orphan")
    service_calls = relationship("ServiceCall", back_populates="restaurant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.OWNER, nullable=False)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    restaurant = relationship("Restaurant", back_populates="users")
    
    __table_args__ = (
        Index("ix_users_email_restaurant", "email", "restaurant_id"),
    )


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    restaurant = relationship("Restaurant", back_populates="categories")
    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    image_url = Column(String(500), nullable=True)
    available = Column(Boolean, default=True)
    featured = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    restaurant = relationship("Restaurant", back_populates="products")
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")


class Table(Base):
    __tablename__ = "tables"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    number = Column(String(20), nullable=False)
    seats = Column(Integer, default=4)
    status = Column(SQLEnum(TableStatus), default=TableStatus.FREE, nullable=False, index=True)
    current_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    qr_token = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    restaurant = relationship("Restaurant", back_populates="tables")
    orders = relationship("Order", back_populates="table", foreign_keys="Order.table_id")

    __table_args__ = (
        UniqueConstraint("restaurant_id", "number", name="uq_table_restaurant_number"),
    )
    
    @property
    def qr_code_url(self):
        from app.core.config import settings
        return f"{settings.BASE_URL.rstrip('/')}/r/qr/{self.qr_token}"


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    table_id = Column(UUID(as_uuid=True), ForeignKey("tables.id", ondelete="SET NULL"), nullable=True, index=True)
    table_number = Column(String(20), nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.RECEIVED, nullable=False, index=True)
    subtotal = Column(Numeric(10, 2), default=0.00)
    service_tax = Column(Numeric(10, 2), default=0.00)
    total = Column(Numeric(10, 2), default=0.00)
    payment_method = Column(SQLEnum(PaymentMethod), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    restaurant = relationship("Restaurant", back_populates="orders")
    table = relationship("Table", back_populates="orders", foreign_keys="Order.table_id")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    restaurant = relationship("Restaurant")
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.WAITER, nullable=False)
    phone = Column(String(50), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    restaurant = relationship("Restaurant", back_populates="employees")


class ServiceCall(Base):
    __tablename__ = "service_calls"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    table_id = Column(UUID(as_uuid=True), ForeignKey("tables.id", ondelete="CASCADE"), nullable=False, index=True)
    table_number = Column(String(20), nullable=False)
    type = Column(SQLEnum(ServiceCallType), nullable=False)
    status = Column(SQLEnum(ServiceCallStatus), default=ServiceCallStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    restaurant = relationship("Restaurant", back_populates="service_calls")
    table = relationship("Table")