"""Pydantic schemas for the billing endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request/Response shapes
# ---------------------------------------------------------------------------
class CheckoutRequest(BaseModel):
    plan: Literal["essencial", "profissional", "escala"]


class CheckoutResponse(BaseModel):
    """Returned by ``POST /billing/checkout``.

    ``url`` is where the frontend should redirect the user (MP's
    ``init_point`` in production, ``sandbox_init_point`` in dev).
    ``preference_id`` is included so the frontend can correlate the
    redirect with the eventual webhook.
    """

    url: str
    preference_id: Optional[str] = None
    sandbox_url: Optional[str] = None


class PortalResponse(BaseModel):
    url: str
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# Plan catalogue
# ---------------------------------------------------------------------------
class PlanInfo(BaseModel):
    name: str
    display_name: str
    base_price: int = Field(..., description="Price in cents (BRL)")
    commission_pct: float
    limits: dict


class PlanListResponse(BaseModel):
    plans: List[PlanInfo]


# ---------------------------------------------------------------------------
# Status of the current subscription
# ---------------------------------------------------------------------------
class BillingStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_name: str
    plan_status: str
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    trial_end: Optional[datetime] = None
    mp_customer_id: Optional[str] = None
    mp_subscription_id: Optional[str] = None
    is_trial: bool = False
    days_until_renewal: Optional[int] = None


# ---------------------------------------------------------------------------
# Admin reports
# ---------------------------------------------------------------------------
class AdminMRRResponse(BaseModel):
    total_mrr: int
    currency: str = "BRL"
    active_subscriptions: int = 0


class AdminRevenueResponse(BaseModel):
    total_revenue: int
    period: str
    currency: str = "BRL"


class AdminChurnResponse(BaseModel):
    churned_count: int
    period: str


class AdminByPlanResponse(BaseModel):
    plan: str
    count: int
    mrr: int


class BillingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    restaurant_id: Optional[UUID]
    mp_event_id: str
    event_type: str
    processed: bool
    error: Optional[str]
    created_at: datetime


# Backwards-compatible alias for older imports that referenced a name
# this module didn't define. Kept here so ``app.schemas.__init__`` keeps
# re-exporting the same public surface it always has.
PlanResponse = PlanInfo
