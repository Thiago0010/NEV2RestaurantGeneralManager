"""SQLAlchemy 2.0 (async) models for the [NEV]2 Restaurant Management System.

Re-exports the shared ``Base`` from :mod:`app.core.database` so Alembic and
tests see a single source of truth. The model definitions intentionally live
in this single module for simplicity (a multi-tenant SaaS of this size does
not benefit from a package-per-table split).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
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


class PlanName(str, enum.Enum):
    NONE = "none"
    ESSENCIAL = "essencial"
    PROFISSIONAL = "profissional"
    ESCALA = "escala"


class PlanStatus(str, enum.Enum):
    NONE = "none"
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    UNPAID = "unpaid"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    welcome_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="R$", nullable=False)
    service_tax_percent: Mapped[float] = mapped_column(
        Numeric(5, 2), default=10.0, nullable=False
    )
    accent_color: Mapped[str] = mapped_column(
        String(16), default="#e07a3c", nullable=False
    )
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    cover_image: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # ---- Mercado Pago / billing ------------------------------------------
    plan_name: Mapped[PlanName] = mapped_column(
        String(20),
        default=PlanName.NONE.value,
        nullable=False,
        index=True,
    )
    plan_status: Mapped[PlanStatus] = mapped_column(
        String(20),
        default=PlanStatus.NONE.value,
        nullable=False,
        index=True,
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    trial_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Mercado Pago specific identifiers
    mp_customer_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, index=True
    )
    mp_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, index=True
    )
    mp_payment_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Legacy fields kept for backwards compatibility with the v0 schema
    # (dropped from the new billing migration but harmless to keep nullable).
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    subscription_item_id_usage: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    # Note: there are TWO FKs between users and restaurants:
    #   users.restaurant_id -> restaurants.id   (employee belongs to a restaurant)
    #   restaurants.owner_id -> users.id       (restaurant has one owner user)
    # When configuring the back-reference on `Restaurant.users` we must
    # explicitly tell SQLAlchemy which FK to use for the join, otherwise
    # it raises "multiple foreign key paths linking the tables".
    users = relationship(
        "User",
        back_populates="restaurant",
        foreign_keys="User.restaurant_id",
    )
    categories = relationship("Category", back_populates="restaurant")
    products = relationship("Product", back_populates="restaurant")
    tables = relationship("Table", back_populates="restaurant")
    orders = relationship("Order", back_populates="restaurant")
    employees = relationship("Employee", back_populates="restaurant")
    service_calls = relationship("ServiceCall", back_populates="restaurant")
    billing_events = relationship(
        "BillingEvent", back_populates="restaurant", cascade="all, delete-orphan"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    role: Mapped[UserRole] = mapped_column(
        String(20), nullable=False, default=UserRole.OWNER.value
    )
    restaurant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=True
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reset_token_hash: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    restaurant = relationship(
        "Restaurant",
        back_populates="users",
        foreign_keys=[restaurant_id],
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    restaurant = relationship("Restaurant", back_populates="categories")
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cost_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("categories.id"), nullable=False
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    preparation_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stock_quantity: Mapped[float] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="unit", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    category = relationship("Category", back_populates="products")
    restaurant = relationship("Restaurant", back_populates="products")


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )
    number: Mapped[str] = mapped_column(String(10), nullable=False)
    seats: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TableStatus.FREE.value,
    )
    qr_token: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    current_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("orders.id"), nullable=True
    )
    opened_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    restaurant = relationship("Restaurant", back_populates="tables")
    current_order = relationship("Order", foreign_keys=[current_order_id])


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )
    table_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tables.id"), nullable=True
    )
    table_number: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=OrderStatus.RECEIVED.value,
    )
    subtotal: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    service_tax: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    total: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(
        Enum(PaymentMethod, name="paymentmethod"), nullable=True
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    restaurant = relationship("Restaurant", back_populates="orders")
    table = relationship("Table", foreign_keys=[table_id])
    items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=True
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    restaurant = relationship("Restaurant")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[UserRole] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.WAITER.value,
    )
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    hire_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    salary: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", foreign_keys=[user_id])
    restaurant = relationship("Restaurant", back_populates="employees")


class ServiceCall(Base):
    __tablename__ = "service_calls"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )
    table_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tables.id"), nullable=True
    )
    # Denormalised table number copied from the referenced table at creation
    # time. The waiter UI and WebSocket broadcasts surface this to the staff
    # without an extra JOIN on every poll, and the public endpoint receives
    # it from the client so we can persist it even when the table_id lookup
    # is skipped (and the relation isn't loaded by the time we serialize).
    table_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    type: Mapped[ServiceCallType] = mapped_column(
        Enum(ServiceCallType, name="servicecalltype"), nullable=False
    )
    status: Mapped[ServiceCallStatus] = mapped_column(
        Enum(ServiceCallStatus, name="servicecallstatus"),
        nullable=False,
        default=ServiceCallStatus.PENDING,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    restaurant = relationship("Restaurant", back_populates="service_calls")
    table = relationship("Table")


class BillingEvent(Base):
    """Audit log of every webhook notification received from Mercado Pago.

    We deduplicate by ``mp_event_id`` (the ``data.id`` from the notification
    payload) so duplicate retries from MP are no-ops.
    """

    __tablename__ = "billing_events"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    mp_event_id: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    restaurant = relationship("Restaurant", back_populates="billing_events")

class InventoryMovement(Base):
    """Audit trail for every stock change (IN/OUT)."""
    __tablename__ = "inventory_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False) # 'IN', 'OUT', 'ADJUSTMENT'
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product = relationship("Product")
    restaurant = relationship("Restaurant")

class ProductRecipe(Base):
    """Bill of Materials (BOM) linking a product to its ingredients."""
    __tablename__ = "product_recipes"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )

    product = relationship("Product", foreign_keys=[product_id])
    ingredient = relationship("Product", foreign_keys=[ingredient_id])
    restaurant = relationship("Restaurant")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

class AuditLog(Base):
    """Log of critical administrative actions for security and compliance."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    restaurant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    device: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserSession(Base):
    """Track active user sessions for concurrent limit control."""
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    token_jti: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    device: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User")



class Expense(Base):
    """Track operational expenses (rent, utilities, etc.)"""
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., 'Rent', 'Electricity', 'Salary'
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    restaurant = relationship("Restaurant")

__all__ = [
    "Base",
    "UserRole",
    "TableStatus",
    "OrderStatus",
    "PaymentMethod",
    "ServiceCallType",
    "ServiceCallStatus",
    "PlanName",
    "PlanStatus",
    "Restaurant",
    "User",
    "Category",
    "Product",
    "Table",
    "Order",
    "OrderItem",
    "Employee",
    "ServiceCall",
    "BillingEvent",
    "InventoryMovement",
    "ProductRecipe",
    "AuditLog",
    "UserSession",
    "Expense",

]
