"""add service_calls.table_number

The customer menu sends ``table_number`` along with ``table_id`` when a
client calls the waiter, and the broadcast payload already surfaces it to
the staff UI. The column was declared on the Pydantic schema but missing
from the ServiceCall ORM model, so any POST to /public/.../service-calls
exploded with ``TypeError: 'table_number' is an invalid keyword argument
for ServiceCall`` -> HTTP 500. This migration adds the column.

Revision ID: c9d4e3f6a7b8
Revises: b8c3d2e5f6a7
Create Date: 2026-08-25 23:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9d4e3f6a7b8"
down_revision: Union[str, None] = "b8c3d2e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable on the DB to match the ORM: existing rows pre-date the
    # public endpoint and have no denormalised number we can reconstruct.
    op.add_column(
        "service_calls",
        sa.Column("table_number", sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("service_calls", "table_number")
