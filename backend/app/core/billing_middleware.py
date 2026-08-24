"""ASGI middleware that blocks API access when the restaurant's plan is
inactive.

The middleware runs *after* CORS but *before* rate limiting/security headers.
It extracts the restaurant from the JWT, looks up the latest billing status,
and returns HTTP 402 if the plan is not ``ACTIVE``/``TRIALING``/``past_due``
(``past_due`` is treated as a soft block: we let the request through and
rely on a banner in the UI; customers typically fix it within a few days).

If the request has no Authorization header (e.g. unauthenticated endpoints
under ``/public``) we let the dependency stack handle it.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Request
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_402_PAYMENT_REQUIRED

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.security import decode_access_token
from app.models import PlanStatus, Restaurant, User

logger = logging.getLogger(__name__)


# Paths that should skip the billing check entirely.
EXCLUDED_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/api/v1/auth",
    "/api/v1/billing",
    "/api/v1/admin/billing",
    "/api/v1/public",
    "/api/v1/webhooks",
    "/api/v1/restaurant/onboarding",
)


ACTIVE_STATUSES = {PlanStatus.ACTIVE, PlanStatus.TRIALING, PlanStatus.PAST_DUE}


class BillingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Fast path: not an API call, or on the exclusion list.
        if not path.startswith("/api/v1/"):
            return await call_next(request)
        if any(path.startswith(p) for p in EXCLUDED_PREFIXES):
            return await call_next(request)

        restaurant = await self._get_restaurant_from_token(request)
        if restaurant is None:
            # Let the auth dependency raise 401 if a token is required.
            return await call_next(request)

        # Apply trial automatically on first request if the restaurant has
        # no status yet. This keeps the dev experience smooth — fresh
        # signups get 7 days of free access.
        restaurant = await self._maybe_activate_trial(restaurant)

        if restaurant.plan_status not in ACTIVE_STATUSES:
            logger.info(
                "Blocking %s for restaurant %s — plan_status=%s",
                path, restaurant.id, restaurant.plan_status.value,
            )
            return JSONResponse(
                status_code=HTTP_402_PAYMENT_REQUIRED,
                content={
                    "detail": (
                        "Plano inativo. Ative uma assinatura para continuar "
                        "usando o [NEV]2 Restaurant Management System."
                    ),
                    "code": "BILLING_REQUIRED",
                    "portal_url": "/api/v1/billing/portal",
                    "checkout_url": "/api/v1/billing/checkout",
                    "current_plan": restaurant.plan_name.value,
                    "plan_status": restaurant.plan_status.value,
                },
            )

        request.state.restaurant = restaurant
        return await call_next(request)

    # ------------------------------------------------------------------
    async def _get_restaurant_from_token(
        self, request: Request
    ) -> Optional[Restaurant]:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth.split(" ", 1)[1].strip()
        payload = decode_access_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None

        try:
            async with async_session_maker() as db:
                user = (
                    await db.execute(select(User).where(User.id == user_id))
                ).scalar_one_or_none()
                if not user or not user.restaurant_id:
                    return None
                return (
                    await db.execute(
                        select(Restaurant).where(
                            Restaurant.id == user.restaurant_id
                        )
                    )
                ).scalar_one_or_none()
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("billing middleware: failed to load user: %s", exc)
            return None

    async def _maybe_activate_trial(
        self, restaurant: Restaurant
    ) -> Restaurant:
        """Activate a free trial for a brand new restaurant.

        Mutates the DB *only* if the restaurant has no plan and trial is
        enabled. We reload the row after commit so the request sees the
        updated status.
        """
        if settings.TRIAL_DAYS <= 0:
            return restaurant
        if restaurant.plan_status != PlanStatus.NONE:
            return restaurant
        if restaurant.plan_name not in (PlanName.NONE,):
            return restaurant

        from datetime import datetime, timedelta, timezone

        try:
            async with async_session_maker() as db:
                # Re-fetch inside this session to avoid mutating a detached
                # object loaded in another session.
                row = (
                    await db.execute(
                        select(Restaurant).where(Restaurant.id == restaurant.id)
                    )
                ).scalar_one_or_none()
                if not row or row.plan_status != PlanStatus.NONE:
                    return row or restaurant

                now = datetime.now(timezone.utc)
                row.plan_status = PlanStatus.TRIALING
                row.plan_name = PlanName.ESSENCIAL  # trial uses the lowest tier
                row.trial_end = now + timedelta(days=settings.TRIAL_DAYS)
                row.current_period_end = row.trial_end
                await db.commit()
                await db.refresh(row)
                return row
        except Exception as exc:  # pragma: no cover
            logger.debug("Could not auto-activate trial: %s", exc)
            return restaurant
