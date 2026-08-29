"""add employee fields (name, role, phone)

Aligns the employees table with the Employee ORM model and the Pydantic
schemas. Previously the table only had user_id/restaurant_id/hire_date/
salary/is_active, which forced the API to surface employee metadata via
a JOIN on the User row. The new columns let the frontend manage an
employee's name/role/phone directly.

Revision ID: a7b2c1d4e5f6
Revises: 8f1d2e3a4b5c
Create Date: 2026-08-25 22:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7b2c1d4e5f6"
down_revision: Union[str, None] = "8f1d2e3a4b5c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the columns with permissive defaults so the migration succeeds even
    # if there are existing rows. We backfill ``name`` from the linked User
    # below and then drop the server defaults.
    op.add_column(
        "employees",
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "employees",
        sa.Column(
            "phone",
            sa.String(length=20),
            nullable=True,
        ),
    )
    op.add_column(
        "employees",
        sa.Column(
            "role",
            sa.Enum(
                "owner", "manager", "waiter", "kitchen",
                name="userrole",
            ),
            nullable=False,
            server_default="waiter",
        ),
    )

    # Backfill name from the backing User row so existing employees render
    # sensibly in the UI without an extra admin step.
    op.execute(
        "UPDATE employees "
        "SET name = COALESCE("
        "  (SELECT full_name FROM users WHERE users.id = employees.user_id),"
        "  ''"
        ") "
        "WHERE name = '' OR name IS NULL"
    )
    # Note: SQLite has no `ALTER COLUMN ... DROP DEFAULT`, so we leave the
    # server defaults in place. They are only used if a caller forgets to
    # supply a value, and the API contract already requires ``name`` and
    # ``role`` in the Pydantic schema.


def downgrade() -> None:
    op.drop_column("employees", "role")
    op.drop_column("employees", "phone")
    op.drop_column("employees", "name")
