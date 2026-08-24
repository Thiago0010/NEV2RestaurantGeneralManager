"""Admin-only billing reports.

The ``require_admin`` dependency accepts either an owner of *any* restaurant
or a superuser. In a real multi-tenant deployment we'd gate this with a
platform-level admin role, but for the MVP the owner is sufficient.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user
from app.core.mercadopago import get_plan_info
from app.models import BillingEvent, PlanName, PlanStatus, Restaurant, User, UserRole
from app.schemas.billing import (
    AdminByPlanResponse,
    AdminChurnResponse,
    AdminMRRResponse,
    AdminRevenueResponse,
    BillingEventRead,
)

router = APIRouter(tags=["admin-billing"])


async def require_admin(
    user: User = Depends(get_current_active_user),
) -> User:
    if not user.is_superuser and user.role not in (UserRole.OWNER, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


@router.get("/mrr", response_model=AdminMRRResponse)
async def get_mrr(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AdminMRRResponse:
    """Sum the base price of every active/trialing subscription."""
    result = await db.execute(
        select(Restaurant.plan_name, func.count(Restaurant.id))
        .where(Restaurant.plan_status.in_([PlanStatus.ACTIVE, PlanStatus.TRIALING]))
        .group_by(Restaurant.plan_name)
    )

    total_mrr = 0
    active = 0
    for plan_name, count in result.all():
        info = get_plan_info(plan_name.value if plan_name else "")
        total_mrr += info.get("base_price_cents", 0) * count
        active += count
    return AdminMRRResponse(total_mrr=total_mrr, active_subscriptions=active)


@router.get("/revenue", response_model=AdminRevenueResponse)
async def get_revenue(
    period: str = Query("month", pattern="^(day|week|month|year)$"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AdminRevenueResponse:
    """Sum the gross revenue of every approved payment in the period."""
    now = datetime.utcnow()
    if period == "day":
        start = now - timedelta(days=1)
    elif period == "week":
        start = now - timedelta(weeks=1)
    elif period == "month":
        start = now - timedelta(days=30)
    else:
        start = now - timedelta(days=365)

    result = await db.execute(
        select(BillingEvent)
        .where(
            BillingEvent.event_type == "payment.approved",
            BillingEvent.created_at >= start,
        )
    )
    total = 0
    for event in result.scalars().all():
        if not event.payload:
            continue
        try:
            data = json.loads(event.payload)
            total += int(float(data.get("transaction_amount", 0)) * 100)
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
    return AdminRevenueResponse(total_revenue=total, period=period)


@router.get("/churn", response_model=AdminChurnResponse)
async def get_churn(
    period: str = Query("month", pattern="^(day|week|month|year)$"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AdminChurnResponse:
    """Count restaurants that moved to ``canceled``/``unpaid`` in the period."""
    now = datetime.utcnow()
    if period == "day":
        start = now - timedelta(days=1)
    elif period == "week":
        start = now - timedelta(weeks=1)
    elif period == "month":
        start = now - timedelta(days=30)
    else:
        start = now - timedelta(days=365)

    result = await db.execute(
        select(BillingEvent)
        .where(
            BillingEvent.event_type.in_(
                ["payment.cancelled", "payment.refunded", "payment.rejected"]
            ),
            BillingEvent.created_at >= start,
        )
    )
    return AdminChurnResponse(
        churned_count=len(result.scalars().all()),
        period=period,
    )


@router.get("/by-plan", response_model=List[AdminByPlanResponse])
async def get_by_plan(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> List[AdminByPlanResponse]:
    """Restaurant count and MRR contribution per plan."""
    result = await db.execute(
        select(Restaurant.plan_name, func.count(Restaurant.id))
        .where(Restaurant.plan_status.in_([PlanStatus.ACTIVE, PlanStatus.TRIALING]))
        .group_by(Restaurant.plan_name)
    )
    out: List[AdminByPlanResponse] = []
    for plan_name, count in result.all():
        info = get_plan_info(plan_name.value if plan_name else "")
        out.append(
            AdminByPlanResponse(
                plan=(plan_name.value if plan_name else "none"),
                count=count,
                mrr=info.get("base_price_cents", 0) * count,
            )
        )
    return out


@router.get("/events", response_model=List[BillingEventRead])
async def list_events(
    restaurant_id: Optional[UUID] = None,
    event_type: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> List[BillingEventRead]:
    """Paginated billing event log (audit trail)."""
    query = select(BillingEvent).order_by(BillingEvent.created_at.desc())
    if restaurant_id:
        query = query.where(BillingEvent.restaurant_id == restaurant_id)
    if event_type:
        query = query.where(BillingEvent.event_type == event_type)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return [BillingEventRead.model_validate(e) for e in result.scalars().all()]
