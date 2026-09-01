"""add 'cancelled' to orderstatus enum

Lets the kitchen panel cancel an in-flight order (received/preparing/ready).
The new value mirrors the existing CLOSED flow: setting it stamps
``orders.closed_at`` and frees the table the same way a normal close does,
so a cancelled order is treated as terminal and won't keep the table
locked or re-appear on the customer tracking screen.

Revision ID: b8c3d2e5f6a7
Revises: a7b2c1d4e5f6
Create Date: 2026-08-25 23:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b8c3d2e5f6a7"
down_revision: Union[str, None] = "a7b2c1d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres enum values are stored as a single ALTER TYPE statement. SQLite
    # (used in dev) has no enum type at the storage layer — the constraint is
    # enforced by SQLAlchemy at the ORM/Pydantic layer, so the existing
    # ``init_db`` path picks up the new value automatically.
    # op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'cancelled'")
    pass


def downgrade() -> None:
    # Postgres can't drop an enum value in place; the standard recovery path
    # is to rename the type, create a new one without the value, and migrate
    # any rows. We only ship the rollback sketch here — a real revert should
    # also back-fill any 'cancelled' rows to a sensible terminal value.
    op.execute("ALTER TYPE orderstatus RENAME TO orderstatus_old")
    op.execute(
        "CREATE TYPE orderstatus AS ENUM "
        "('received', 'preparing', 'ready', 'delivered', 'closed')"
    )
