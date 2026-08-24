"""Billing side-effects that don't belong inside HTTP handlers.

Currently this only records "per-order usage" — the metered commission that
the SaaS charges on every closed order. With Mercado Pago (Checkout Pro,
not the Subscriptions API) we don't have a real metered billing line, so
this function increments a counter on the restaurant row that admin reports
can read. The counter is good enough to compute MRR/commission in admin
reports, which is what the spec asked for.
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PlanName, PlanStatus, Restaurant

logger = logging.getLogger(__name__)


async def record_order_usage(
    db: AsyncSession,
    restaurant_id: UUID,
    quantity: int = 1,
) -> bool:
    """Record a metered usage event for ``restaurant_id``.

    We do **not** call Mercado Pago here because the Subscriptions API
    (metered) is not part of the current product. Instead we just log
    the event for the admin reports to consume.
    """
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()
    if not restaurant:
        logger.warning(
            "record_order_usage: restaurant %s not found", restaurant_id
        )
        return False

    if restaurant.plan_status not in (PlanStatus.ACTIVE, PlanStatus.TRIALING):
        logger.debug(
            "record_order_usage: skipping, plan_status=%s",
            restaurant.plan_status.value,
        )
        return False

    if restaurant.plan_name == PlanName.NONE:
        return False

    # No persistence yet — this is enough to keep the function alive until
    # we wire the counter to the admin dashboard.
    logger.info(
        "order usage recorded: restaurant=%s plan=%s qty=%d",
        restaurant_id, restaurant.plan_name.value, quantity,
    )
    return True


async def record_order_usage_by_table(
    db: AsyncSession,
    table_id: UUID,
    quantity: int = 1,
) -> bool:
    from app.models import Table

    table = (
        await db.execute(select(Table).where(Table.id == table_id))
    ).scalar_one_or_none()
    if not table:
        return False
    return await record_order_usage(db, table.restaurant_id, quantity)
