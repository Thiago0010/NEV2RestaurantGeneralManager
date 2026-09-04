"""Mercado Pago SDK helpers.

We use the official ``mercadopago`` Python SDK and keep a single SDK instance
cached for the process lifetime. The wrappers here are intentionally thin —
they translate our domain language (plans, restaurants) into the shape
Mercado Pago's API expects.

For a SaaS, the integration is "Checkout Pro" (one preference per billing
period) instead of Subscriptions API. This is the simplest reliable flow:
the customer is redirected to MP, pays, MP sends a webhook with the
``payment`` topic, and we activate the plan. The customer can manage
their subscription via the ``/billing/portal`` endpoint which points at
MP's account management page (no separate "Billing Portal" product in
Mercado Pago like Stripe has).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from functools import lru_cache
from typing import Any, Dict, Optional

import mercadopago
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import PlanName, Restaurant

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Plan catalogue
# ---------------------------------------------------------------------------
PLAN_CATALOG: Dict[str, Dict[str, Any]] = {
    PlanName.ESSENCIAL.value: {
        "name": PlanName.ESSENCIAL.value,
        "display_name": "Ilimitado",
        "base_price_cents": settings.MP_PRICE_ESSENCIAL,
        "commission_pct": 1.5,
        "limits": {
            "tables": 10000,
            "employees": 1000,
            "products": 721
        },
    },
}


def get_plan_info(plan: str) -> Dict[str, Any]:
    """Return the catalogue entry for a plan or an empty dict if unknown."""
    return PLAN_CATALOG.get(plan.lower(), {})


def all_plans() -> list[Dict[str, Any]]:
    """Return the full plan catalogue (used by ``GET /billing/plans``)."""
    return list(PLAN_CATALOG.values())


# ---------------------------------------------------------------------------
# SDK
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_mp_client() -> mercadopago.SDK:
    """Return a cached Mercado Pago SDK client.

    The SDK is stateful only insofar as the access token is configured, so a
    single shared instance is fine. If the token is empty we still return an
    SDK — calls will fail at runtime, which gives a clearer error to the
    developer than failing on import.
    """
    if not settings.MP_ACCESS_TOKEN:
        logger.warning(
            "MP_ACCESS_TOKEN is not set — Mercado Pago calls will fail. "
            "Set it in backend/.env to enable real billing."
        )
    return mercadopago.SDK(settings.MP_ACCESS_TOKEN)


# ---------------------------------------------------------------------------
# Preference creation
# ---------------------------------------------------------------------------
async def create_checkout_preference(
    db: AsyncSession,
    restaurant: Restaurant,
    plan: str,
) -> dict[str, Any]:
    """Create a Mercado Pago Checkout Pro preference for ``plan``.

    Returns the ``init_point`` (production) and ``sandbox_init_point`` (test)
    URLs the frontend should redirect the user to. The preference stores
    ``restaurant_id`` and ``plan`` in ``external_reference`` (we use a JSON
    blob to keep the data round-trip safe) so the webhook can resolve the
    restaurant without a database lookup.
    """
    info = get_plan_info(plan)
    if not info:
        raise ValueError(f"Unknown plan '{plan}'")

    import json

    external_reference = json.dumps(
        {"restaurant_id": str(restaurant.id), "plan": plan},
        separators=(",", ":"),
    )

    # Mercado Pago requires absolute URLs in back_url when auto_return is set.
    # Normalise FRONTEND_URL (strip trailing slash, fall back to BASE_URL) so
    # we never send a malformed URL like "None/settings?checkout=success" or
    # "http://localhost:5173//settings?...\" which makes MP reject the
    # preference with "auto_return invalid. back_url.success must be defined".
    frontend_base = (settings.FRONTEND_URL or settings.BACKEND_URL or "").rstrip("/")
    if not frontend_base:
        raise RuntimeError(
            "FRONTEND_URL (or BASE_URL) is not configured — cannot build "
            "Mercado Pago back_urls."
        )

    # Mercado Pago's auto_return="approved" rejects back_urls that contain
    # query strings — and ALSO requires the URLs to be HTTPS on a
    # non-localhost host. In dev (HTTP/localhost) we can include a
    # `?checkout=...` query param so the frontend can react to the redirect
    # (toast + refetch). In production we keep the URLs bare (no query
    # string) to satisfy MP's strict validation, and the SPA is responsible
    # for polling /billing/status on mount to detect the activation.
    is_production_redirect = (
        frontend_base.startswith("https://") and "localhost" not in frontend_base
    )
    if is_production_redirect:
        success_url = f"{frontend_base}/settings"
        failure_url = f"{frontend_base}/settings"
        pending_url = f"{frontend_base}/settings"
    else:
        success_url = f"{frontend_base}/settings?checkout=success"
        failure_url = f"{frontend_base}/settings?checkout=failure"
        pending_url = f"{frontend_base}/settings?checkout=pending"

    sdk = get_mp_client()
    preference_data: Dict[str, Any] = {
        "items": [
            {
                "title": f"[NEV]2 Restaurant Management System — Plano {info['display_name']}",
                "description": (
                    f"Assinatura mensal [NEV]2 Restaurant Management System "
                    f"({info['commission_pct']}% de comissão por pedido)"
                ),
                "quantity": 1,
                "unit_price": info["base_price_cents"] / 100.0,
                "currency_id": "BRL",
            }
        ],
        "back_urls": {
            "success": success_url,
            "failure": failure_url,
            "pending": pending_url,
        },
        "external_reference": external_reference,
        "metadata": {
            "restaurant_id": str(restaurant.id),
            "plan": plan,
        },
        "notification_url": (
            f"{settings.BACKEND_URL}/api/v1/billing/webhooks/mercadopago"
        ),
    }

    # Enable auto_return only on production HTTPS — see the redirect note
    # above for the reason. The "auto_return invalid. back_url.success must
    # be defined" 400 is a misleading error MP returns when either the URL
    # is HTTP/localhost or it contains a query string.
    if is_production_redirect:
        preference_data["auto_return"] = "approved"
    logger.info(
        "Mercado Pago preference data: success_url=%s, failure_url=%s, pending_url=%s, auto_return=%s, notification_url=%s",
        success_url,
        failure_url,
        pending_url,
        preference_data.get("auto_return"),
        preference_data.get("notification_url"),
    )
    logger.debug("Full preference payload: %s", preference_data)
    response = sdk.preference().create(preference_data)
    if response.get("status") not in (200, 201):
        logger.error("Mercado Pago preference creation failed: %s", response)
        raise RuntimeError(
            f"Failed to create Mercado Pago preference: {response}"
        )

    return response["response"]
# ---------------------------------------------------------------------------
# Payment lookup & webhook verification
# ---------------------------------------------------------------------------
def get_payment(payment_id: str | int) -> Dict[str, Any]:
    """Fetch a single payment from Mercado Pago by id.

    Raises if the API returns non-200 so the webhook handler can decide
    whether to retry. Idempotency is handled by ``BillingEvent``.
    """
    sdk = get_mp_client()
    response = sdk.payment().get(payment_id)
    if response.get("status") != 200:
        raise RuntimeError(
            f"Failed to fetch payment {payment_id}: {response}"
        )
    return response["response"]


def verify_webhook_signature(
    x_signature: Optional[str],
    x_request_id: Optional[str],
    body: bytes,
    *,
    data_id: Optional[str] = None,
) -> bool:
    """Verify the HMAC-SHA256 signature Mercado Pago sends on webhooks.

    The signature is built as:
        ``manifest = f"id={data_id};request-id={x_request_id};ts={ts};"``
        ``hmac_sha256(manifest, MP_WEBHOOK_SECRET)``

    We compare it in constant time. If ``MP_WEBHOOK_SECRET`` is not set we
    return ``True`` (development mode) and log a warning — this is the same
    behaviour as the original Stripe-era middleware.
    """
    secret = settings.MP_WEBHOOK_SECRET
    if not secret:
        logger.error(
            "CRITICAL: MP_WEBHOOK_SECRET not configured. Webhook verification "
            "cannot be performed. Set this in .env to enable secure payments."
        )
        return False

    if not x_signature or not x_request_id or not data_id:
        logger.warning(
            "Missing Mercado Pago signature headers (x-signature=%s, "
            "x-request-id=%s, data_id=%s)",
            bool(x_signature), bool(x_request_id), bool(data_id),
        )
        return False

    # The x-signature header looks like ``ts=1234, v1=abcdef...``
    parts: dict[str, str] = {}
    for chunk in x_signature.split(","):
        if "=" in chunk:
            key, _, value = chunk.strip().partition("=")
            parts[key] = value

    ts = parts.get("ts")
    received_hash = parts.get("v1")
    if not ts or not received_hash:
        logger.warning("Mercado Pago signature missing ts/v1")
        return False

    manifest = f"id={data_id};request-id={x_request_id};ts={ts};"
    expected = hmac.new(
        secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, received_hash)


def build_portal_url() -> str:
    """Return the URL where the user can manage their Mercado Pago account.

    Mercado Pago does not have a hosted "Billing Portal" like Stripe, so we
    point the customer at MP's subscription management page. The customer
    can cancel/refund there and we'll be notified via webhook.
    """
    if settings.MP_ENVIRONMENT == "production":
        return "https://www.mercadopago.com.br/subscriptions"
    return "https://sandbox.mercadopago.com.br/subscriptions"