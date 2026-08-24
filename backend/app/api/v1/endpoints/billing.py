"""Billing endpoints — checkout, portal, status, plans, webhook."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, get_restaurant_from_user
from app.core.config import settings
from app.core.mercadopago import (
    all_plans,
    build_portal_url,
    create_checkout_preference,
    get_payment,
    get_plan_info,
    verify_webhook_signature,
)
from app.models import BillingEvent, PlanName, PlanStatus, Restaurant, User
from app.schemas.billing import (
    BillingStatus,
    CheckoutRequest,
    CheckoutResponse,
    PlanInfo,
    PlanListResponse,
    PortalResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------
@router.get("/plans", response_model=PlanListResponse)
async def list_plans() -> PlanListResponse:
    """Return the static plan catalogue. No auth required — used on the
    public marketing/pricing page before the user signs up."""
    plans = [
        PlanInfo(
            name=p["name"],
            display_name=p["display_name"],
            base_price=p["base_price_cents"],
            commission_pct=p["commission_pct"],
            limits=p["limits"],
        )
        for p in all_plans()
    ]
    return PlanListResponse(plans=plans)


# ---------------------------------------------------------------------------
# Authenticated billing actions
# ---------------------------------------------------------------------------
@router.post(
    "/checkout", response_model=CheckoutResponse, status_code=status.HTTP_200_OK
)
async def create_checkout(
    body: CheckoutRequest,
    restaurant: Restaurant = Depends(get_restaurant_from_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """Create a Mercado Pago Checkout Pro preference and return its URL.

    The frontend should redirect the user to ``url`` (``sandbox_url`` in dev)
    to complete the payment. We don't store the preference id — the webhook
    is idempotent via ``BillingEvent.mp_event_id`` and the payment's
    ``external_reference`` carries the restaurant id.
    """
    if not settings.MP_ACCESS_TOKEN:
        raise HTTPException(
            status_code=503,
            detail=(
                "Mercado Pago não está configurado neste ambiente. "
                "Defina MP_ACCESS_TOKEN no backend/.env ou aguarde o trial "
                "automático de 7 dias expirar para testar o fluxo de bloqueio."
            ),
        )

    try:
        pref = await create_checkout_preference(db, restaurant, body.plan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_checkout_preference failed")
        raise HTTPException(
            status_code=502, detail=f"Mercado Pago error: {exc}"
        ) from exc

    return CheckoutResponse(
        url=pref.get("init_point") or pref.get("sandbox_init_point") or "",
        sandbox_url=pref.get("sandbox_init_point"),
        preference_id=pref.get("id"),
    )


@router.post("/portal", response_model=PortalResponse)
async def open_portal(
    _user: User = Depends(get_current_active_user),
) -> PortalResponse:
    """Return a URL where the user can manage their Mercado Pago subscription.

    Mercado Pago doesn't expose a hosted "Billing Portal" product, so we
    point the customer at MP's subscription management page. They can cancel
    there and we'll be notified via webhook.
    """
    return PortalResponse(
        url=build_portal_url(),
        note=(
            "Mercado Pago gerencia sua assinatura nesta página. "
            "Cancelamentos e reembolsos são processados pelo MP e refletem "
            "aqui automaticamente."
        ),
    )


@router.get("/status", response_model=BillingStatus)
async def get_billing_status(
    restaurant: Restaurant = Depends(get_restaurant_from_user),
) -> BillingStatus:
    """Return the current billing state for the authenticated restaurant."""
    days_until_renewal: Optional[int] = None
    if restaurant.current_period_end:
        delta = restaurant.current_period_end - datetime.now(timezone.utc)
        days_until_renewal = max(0, delta.days)

    is_trial = restaurant.plan_status == PlanStatus.TRIALING

    return BillingStatus(
        plan_name=restaurant.plan_name.value,
        plan_status=restaurant.plan_status.value,
        current_period_end=restaurant.current_period_end,
        cancel_at_period_end=restaurant.cancel_at_period_end,
        trial_end=restaurant.trial_end,
        mp_customer_id=restaurant.mp_customer_id,
        mp_subscription_id=restaurant.mp_subscription_id,
        is_trial=is_trial,
        days_until_renewal=days_until_renewal,
    )


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------
@router.post("/webhooks/mercadopago")
async def mercadopago_webhook(
    request: Request,
    x_signature: Optional[str] = Header(None, alias="x-signature"),
    x_request_id: Optional[str] = Header(None, alias="x-request-id"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Process a Mercado Pago webhook notification."""
    logger.info("Mercado Pago webhook received")
    body = await request.body()
    try:
        payload: Dict[str, Any] = json.loads(body or b"{}")
        logger.info(f"Mercado Pago webhook payload: {payload}")
    except json.JSONDecodeError:
        logger.error("Mercado Pago webhook: invalid JSON")
        return {"status": "ignored", "reason": "invalid_json"}

    # Coerce payment_id: it can be a string, an int, or a UUID-shaped id
    # depending on the topic.
    payment_id: Optional[str] = None
    topic = payload.get("topic") or payload.get("type")
    data = payload.get("data") or {}
    if isinstance(data, dict):
        payment_id = data.get("id")
    if not payment_id:
        payment_id = payload.get("id")
    if payment_id is not None:
        payment_id = str(payment_id)
    logger.info(f"Mercado Pago webhook: payment_id={payment_id}, topic={topic}")

    if not payment_id:
        # merchant_order / preapproval — we don't process these directly.
        logger.info("Mercado Pago webhook: no payment id, topic=%s", topic)
        return {"status": "ignored", "reason": "no_payment_id"}

    # Idempotency: short-circuit if we've already seen this event id.
    existing = (
        await db.execute(
            select(BillingEvent).where(BillingEvent.mp_event_id == payment_id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        logger.info("Mercado Pago webhook: duplicate %s, ignoring", payment_id)
        return {"status": "duplicate"}

    # Signature verification (skipped if MP_WEBHOOK_SECRET is not set).
    if not verify_webhook_signature(
        x_signature=x_signature,
        x_request_id=x_request_id,
        body=body,
        data_id=payment_id,
    ):
        logger.warning("Mercado Pago webhook: bad signature for %s", payment_id)
        # 200 to avoid infinite retries, but we DO NOT mark the event as
        # processed so admin reports can flag it.
        return {"status": "invalid_signature"}

    # Fetch the canonical payment from Mercado Pago. We never trust the
    # payload directly — it can be tampered with in transit.
    try:
        payment = get_payment(payment_id)
        logger.info(f"Mercado Pago webhook: fetched payment {payment_id}: {payment}")
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch payment %s: %s", payment_id, exc)
        return {"status": "fetch_failed"}

    # Resolve restaurant from external_reference or metadata.
    restaurant_id: Optional[UUID] = None
    plan_name_hint: Optional[str] = None

    ext_ref = payment.get("external_reference")
    if isinstance(ext_ref, str) and ext_ref:
        try:
            ext = json.loads(ext_ref)
            if isinstance(ext, dict):
                rid = ext.get("restaurant_id")
                if rid:
                    restaurant_id = UUID(rid)
                plan_name_hint = ext.get("plan")
        except (json.JSONDecodeError, ValueError):
            # legacy: ext_ref was the raw uuid
            try:
                restaurant_id = UUID(ext_ref)
            except ValueError:
                pass

    if restaurant_id is None:
        meta = payment.get("metadata") or {}
        if isinstance(meta, dict):
            rid = meta.get("restaurant_id")
            if rid:
                try:
                    restaurant_id = UUID(str(rid))
                except ValueError:
                    pass
            plan_name_hint = plan_name_hint or meta.get("plan")

    if restaurant_id is None:
        logger.warning(
            "Mercado Pago webhook: cannot resolve restaurant for %s", payment_id
        )
        # Still record the event for audit.
        db.add(
            BillingEvent(
                mp_event_id=payment_id,
                event_type=f"payment.{payment.get('status', 'unknown')}",
                payload=json.dumps(payment, default=str),
                processed=False,
                error="restaurant_not_resolved",
            )
        )
        await db.commit()
        return {"status": "ignored", "reason": "no_restaurant"}

    # Look up the restaurant and apply the status change.
    restaurant = (
        await db.execute(
            select(Restaurant).where(Restaurant.id == restaurant_id)
        )
    ).scalar_one_or_none()
    if restaurant is None:
        logger.warning(
            "Mercado Pago webhook: restaurant %s not found", restaurant_id
        )
        return {"status": "ignored", "reason": "restaurant_not_found"}
    logger.info(f"Mercado Pago webhook: found restaurant {restaurant.id} (plan_name={restaurant.plan_name}, plan_status={restaurant.plan_status})")
    status_mp = payment.get("status")
    applied = _apply_payment_to_restaurant(restaurant, payment, plan_name_hint)
    logger.info(f"Mercado Pago webhook: _apply_payment_to_restaurant returned applied={applied}")
    db.add(
        BillingEvent(
            restaurant_id=restaurant.id,
            mp_event_id=payment_id,
            event_type=f"payment.{status_mp}",
            payload=json.dumps(payment, default=str),
            processed=applied,
            error=None if applied else "no_change",
        )
    )
    await db.commit()
    logger.info(f"Mercado Pago webhook: committed changes for payment {payment_id}")
    return {"status": "ok", "applied": applied}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _apply_payment_to_restaurant(
    restaurant: Restaurant,
    payment: Dict[str, Any],
    plan_name_hint: Optional[str],
) -> bool:
    """Mutate ``restaurant`` in place based on a Mercado Pago payment.

    Returns ``True`` if any field was changed, ``False`` otherwise. The
    caller is responsible for committing.
    """
    changed = False
    status_mp = payment.get("status")

    # Resolve plan name: prefer the explicit metadata, fall back to the
    # item title (e.g. "[NEV]2 Restaurant Management System — Plano Essencial").
    resolved_plan: Optional[PlanName] = None
    if plan_name_hint:
        try:
            resolved_plan = PlanName(plan_name_hint)
        except ValueError:
            resolved_plan = None
    if resolved_plan is None:
        items = payment.get("additional_info", {}).get("items") or []
        if items:
            title = (items[0].get("title") or "").lower()
            for candidate in PlanName:
                if candidate.value in title:
                    resolved_plan = candidate
                    break

    if status_mp == "approved":
        if restaurant.plan_status != PlanStatus.ACTIVE:
            restaurant.plan_status = PlanStatus.ACTIVE
            changed = True
        if resolved_plan is not None and restaurant.plan_name != resolved_plan:
            restaurant.plan_name = resolved_plan
            changed = True
        # MP doesn't give us a real period end in Checkout Pro — estimate
        # it as +30 days from the payment date. Webhooks for renewals
        # (separate preference) will refresh this.
        period_end = _period_end_from_payment(payment)
        if period_end and restaurant.current_period_end != period_end:
            restaurant.current_period_end = period_end
            changed = True
        if restaurant.cancel_at_period_end:
            restaurant.cancel_at_period_end = False
            changed = True
        if payment.get("id") is not None:
            restaurant.mp_payment_id = str(payment["id"])
            changed = True
        if payment.get("payer", {}).get("id") and not restaurant.mp_customer_id:
            restaurant.mp_customer_id = str(payment["payer"]["id"])
            changed = True
        return changed

    if status_mp in ("rejected", "cancelled", "expired", "refunded"):
        if restaurant.plan_status not in (PlanStatus.CANCELED, PlanStatus.UNPAID):
            restaurant.plan_status = (
                PlanStatus.UNPAID if status_mp == "rejected" else PlanStatus.CANCELED
            )
            changed = True
        return changed

    # pending / in_process / authorized — leave the plan alone but log.
    return False


def _period_end_from_payment(payment: Dict[str, Any]) -> Optional[datetime]:
    """Best-effort period end computation for a Checkout Pro payment.

    MP's payment object includes ``date_approved`` (ISO) but not a real
    subscription period. We use it as the anchor and add 30 days, which
    matches the monthly cadence we sell at.
    """
    raw = (
        payment.get("date_approved")
        or payment.get("date_created")
    )
    if not raw:
        return None
    try:
        # MP dates look like "2024-01-02T03:04:05.000-03:00" or with "Z".
        cleaned = raw.replace("Z", "+00:00")
        anchor = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=timezone.utc)
    return anchor + timedelta(days=30)
