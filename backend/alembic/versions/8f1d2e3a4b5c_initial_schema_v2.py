"""initial schema v2

This migration replaces the previous (v1, SQLAlchemy-1.x) migration. It
creates every table from scratch using the new 2.0 models, so it's safe to
apply against a brand-new database. If you're upgrading from v1, the
recommended path is to back up ``restaurant_nev2.db`` and start fresh —
the schema is incompatible at the column level.

Revision ID: 8f1d2e3a4b5c
Revises:
Create Date: 2026-08-21 20:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f1d2e3a4b5c"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ users
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("role", sa.Enum("owner", "manager", "waiter", "kitchen", name="userrole"), nullable=False, server_default="owner"),
        sa.Column("restaurant_id", sa.UUID(), nullable=True),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_restaurant_id", "users", ["restaurant_id"], unique=False)

    # ----------------------------------------------------------- restaurants
    op.create_table(
        "restaurants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("welcome_message", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="R$"),
        sa.Column("service_tax_percent", sa.Numeric(5, 2), nullable=False, server_default="10.0"),
        sa.Column("accent_color", sa.String(length=16), nullable=False, server_default="#e07a3c"),
        sa.Column("logo_url", sa.String(length=512), nullable=True),
        sa.Column("cover_image", sa.String(length=512), nullable=True),
        # Billing / MP
        sa.Column("plan_name", sa.Enum("none", "essencial", "profissional", "escala", name="planname"), nullable=False, server_default="none"),
        sa.Column("plan_status", sa.Enum("none", "active", "trialing", "past_due", "canceled", "incomplete", "incomplete_expired", "unpaid", name="planstatus"), nullable=False, server_default="none"),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mp_customer_id", sa.String(length=128), nullable=True),
        sa.Column("mp_subscription_id", sa.String(length=128), nullable=True),
        sa.Column("mp_payment_id", sa.String(length=128), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=128), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=128), nullable=True),
        sa.Column("subscription_item_id_usage", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_restaurants_slug", "restaurants", ["slug"], unique=True)
    op.create_index("ix_restaurants_plan_name", "restaurants", ["plan_name"], unique=False)
    op.create_index("ix_restaurants_plan_status", "restaurants", ["plan_status"], unique=False)
    op.create_index("ix_restaurants_mp_customer_id", "restaurants", ["mp_customer_id"], unique=False)
    op.create_index("ix_restaurants_mp_subscription_id", "restaurants", ["mp_subscription_id"], unique=False)

    # owner FK (created after users)
    op.create_foreign_key(
        "fk_restaurants_owner_id_users",
        "restaurants", "users",
        ["owner_id"], ["id"],
    )

    # ----------------------------------------------------------- categories
    op.create_table(
        "categories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("restaurant_id", sa.UUID(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # ------------------------------------------------------------- products
    op.create_table(
        "products",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("restaurant_id", sa.UUID(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("image_url", sa.String(length=512), nullable=True),
        sa.Column("preparation_time", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # --------------------------------------------------------------- tables
    op.create_table(
        "tables",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("restaurant_id", sa.UUID(), nullable=False),
        sa.Column("number", sa.String(length=10), nullable=False),
        sa.Column("seats", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("status", sa.Enum("free", "occupied", "waiting", "preparing", "bill_requested", "closing", name="tablestatus"), nullable=False, server_default="free"),
        sa.Column("qr_token", sa.String(length=255), nullable=False),
        sa.Column("current_order_id", sa.UUID(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("qr_token"),
    )
    op.create_index("ix_tables_qr_token", "tables", ["qr_token"], unique=True)

    # --------------------------------------------------------------- orders
    op.create_table(
        "orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("restaurant_id", sa.UUID(), nullable=False),
        sa.Column("table_id", sa.UUID(), nullable=True),
        sa.Column("table_number", sa.String(length=10), nullable=False),
        sa.Column("status", sa.Enum("received", "preparing", "ready", "delivered", "closed", name="orderstatus"), nullable=False, server_default="received"),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("service_tax", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("payment_method", sa.Enum("cash", "pix", "card", "other", name="paymentmethod"), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ----------------------------------------------------------- order_items
    op.create_table(
        "order_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("restaurant_id", sa.UUID(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_tables_current_order_id_orders",
        "tables", "orders",
        ["current_order_id"], ["id"],
        ondelete="SET NULL",
    )

    # ------------------------------------------------------------ employees
    op.create_table(
        "employees",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("restaurant_id", sa.UUID(), nullable=False),
        sa.Column("hire_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("salary", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # -------------------------------------------------------- service_calls
    op.create_table(
        "service_calls",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("restaurant_id", sa.UUID(), nullable=False),
        sa.Column("table_id", sa.UUID(), nullable=True),
        sa.Column("type", sa.Enum("help", "order", "bill", name="servicecalltype"), nullable=False),
        sa.Column("status", sa.Enum("pending", "assumed", "resolved", name="servicecallstatus"), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # --------------------------------------------------------- billing_events
    op.create_table(
        "billing_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("restaurant_id", sa.UUID(), nullable=True),
        sa.Column("mp_event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mp_event_id"),
    )
    op.create_index("ix_billing_events_mp_event_id", "billing_events", ["mp_event_id"], unique=True)
    op.create_index("ix_billing_events_restaurant_id", "billing_events", ["restaurant_id"], unique=False)
    op.create_index("ix_billing_events_event_type", "billing_events", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_billing_events_event_type", table_name="billing_events")
    op.drop_index("ix_billing_events_restaurant_id", table_name="billing_events")
    op.drop_index("ix_billing_events_mp_event_id", table_name="billing_events")
    op.drop_table("billing_events")

    op.drop_table("service_calls")
    op.drop_table("employees")
    op.drop_constraint("fk_tables_current_order_id_orders", "tables", type_="foreignkey")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_index("ix_tables_qr_token", table_name="tables")
    op.drop_table("tables")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_constraint("fk_restaurants_owner_id_users", "restaurants", type_="foreignkey")
    op.drop_index("ix_restaurants_mp_subscription_id", table_name="restaurants")
    op.drop_index("ix_restaurants_mp_customer_id", table_name="restaurants")
    op.drop_index("ix_restaurants_plan_status", table_name="restaurants")
    op.drop_index("ix_restaurants_plan_name", table_name="restaurants")
    op.drop_index("ix_restaurants_slug", table_name="restaurants")
    op.drop_table("restaurants")
    op.drop_index("ix_users_restaurant_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
