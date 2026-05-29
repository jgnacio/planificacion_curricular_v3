import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, UTC
from typing import Any

import calendar

import mercadopago
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.billing import (
    IndividualSubscription,
    InstitutionBillingCycle,
    MpPlan,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET", os.getenv("MP_SECRET_KEY", ""))


def _get_sdk() -> mercadopago.SDK:
    token = os.getenv("MP_ACCESS_TOKEN", "")
    if not token:
        raise HTTPException(status_code=500, detail="MP_ACCESS_TOKEN not configured")
    return mercadopago.SDK(token)


def _verify_mp_signature(
    x_signature: str | None,
    x_request_id: str | None,
    data_id: str,
) -> bool:
    """Verifica HMAC-SHA256 contra el manifest oficial de MP.

    Manifest: id:[data.id];request-id:[x-request-id];ts:[ts];
    """
    if not MP_WEBHOOK_SECRET or not x_signature or not x_request_id:
        return False
    try:
        parts = dict(p.strip().split("=", 1) for p in x_signature.split(","))
        ts = parts.get("ts", "")
        v1 = parts.get("v1", "")
        if not ts or not v1:
            return False
        manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
        expected = hmac.new(
            MP_WEBHOOK_SECRET.encode(),
            manifest.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, v1)
    except Exception as e:
        logger.warning("MP signature parse error: %s", e)
        return False


def _add_months(d: datetime, months: int) -> datetime:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return d.replace(year=year, month=month, day=day)


def _compute_period_end(start: datetime, billing_period: str) -> datetime:
    return _add_months(start, 12 if billing_period == "annual" else 1)


def _handle_preapproval_event(data_id: str, db: Session) -> None:
    """Sincroniza el status local con MP consultando la API.

    El webhook NO trae el status — solo el data.id. Hay que consultar.
    """
    sdk = _get_sdk()
    result = sdk.subscription().get(data_id)
    if result["status"] != 200:
        logger.error("MP preapproval fetch failed for %s: %s", data_id, result.get("response"))
        return

    mp_data: dict[str, Any] = result["response"]
    mp_status = mp_data.get("status", "")
    payer_id = str(mp_data.get("external_reference") or mp_data.get("payer_id") or "")
    mp_plan_id = mp_data.get("preapproval_plan_id")

    sub = db.query(IndividualSubscription).filter(
        IndividualSubscription.mp_preapproval_id == data_id
    ).first()

    if sub:
        sub.status = mp_status
        if mp_status == "cancelled" and not sub.canceled_at:
            sub.canceled_at = datetime.now(UTC)
        db.commit()
        return

    # No existe localmente — crear si tenemos el plan y el usuario
    if not (payer_id and mp_plan_id and mp_status == "authorized"):
        return

    plan = db.query(MpPlan).filter(MpPlan.mp_plan_id == mp_plan_id).first()
    if not plan:
        logger.warning("Webhook preapproval %s references unknown mp_plan_id=%s", data_id, mp_plan_id)
        return

    now = datetime.now(UTC)
    sub = IndividualSubscription(
        user_id=payer_id,
        mp_plan_id=plan.id,
        mp_preapproval_id=data_id,
        status=mp_status,
        current_period_start=now,
        current_period_end=_compute_period_end(now, plan.billing_period),
    )
    db.add(sub)
    db.commit()


def _handle_authorized_payment(data_id: str, db: Session) -> None:
    """Renueva el período cuando MP cobra el pago recurrente."""
    sdk = _get_sdk()
    # El SDK Python expone esto bajo el resource general; fallback a HTTP raw si falla
    try:
        payment_resource = sdk.subscription_authorized_payment()
        result = payment_resource.get(data_id)
    except AttributeError:
        # SDK viejo — usar HTTP raw
        result = sdk.get(f"/authorized_payments/{data_id}")

    if result.get("status") != 200:
        logger.error("MP authorized_payment fetch failed for %s: %s", data_id, result.get("response"))
        return

    payment_data: dict[str, Any] = result["response"]
    preapproval_id = payment_data.get("preapproval_id")
    payment_status = payment_data.get("status", "")
    if not preapproval_id or payment_status != "approved":
        return

    sub = db.query(IndividualSubscription).filter(
        IndividualSubscription.mp_preapproval_id == preapproval_id
    ).first()
    if not sub:
        logger.warning("Authorized payment %s references unknown preapproval %s", data_id, preapproval_id)
        return

    plan = db.query(MpPlan).filter(MpPlan.id == sub.mp_plan_id).first()
    billing_period = plan.billing_period if plan else "monthly"

    now = datetime.now(UTC)
    sub.current_period_start = now
    sub.current_period_end = _compute_period_end(now, billing_period)
    if sub.status != "authorized":
        sub.status = "authorized"
    db.commit()


@router.post("/mp/individual")
async def mp_individual_webhook(
    request: Request,
    x_signature: str | None = Header(None),
    x_request_id: str | None = Header(None),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    body = await request.body()
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    data_id = str(payload.get("data", {}).get("id", ""))
    if not data_id:
        return {"status": "no_id"}

    if MP_WEBHOOK_SECRET and not _verify_mp_signature(x_signature, x_request_id, data_id):
        raise HTTPException(status_code=401, detail="Invalid MP signature")

    event_type = payload.get("type", "")

    try:
        if event_type == "subscription_preapproval":
            _handle_preapproval_event(data_id, db)
        elif event_type == "subscription_authorized_payment":
            _handle_authorized_payment(data_id, db)
        else:
            return {"status": "ignored"}
    except Exception as e:
        logger.error("Webhook handler error: %s", e, exc_info=True)
        # Devolver 200 igual para evitar reintentos infinitos cuando el error es nuestro
        return {"status": "error", "message": str(e)}

    return {"status": "ok"}


@router.post("/mp/institutional")
async def mp_institutional_webhook(
    request: Request,
    x_signature: str | None = Header(None),
    x_request_id: str | None = Header(None),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    body = await request.body()
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    data_id = str(payload.get("data", {}).get("id", ""))
    if not data_id:
        return {"status": "no_id"}

    if MP_WEBHOOK_SECRET and not _verify_mp_signature(x_signature, x_request_id, data_id):
        raise HTTPException(status_code=401, detail="Invalid MP signature")

    if payload.get("type") != "payment":
        return {"status": "ignored"}

    # Consultar el pago real a MP
    sdk = _get_sdk()
    result = sdk.payment().get(data_id)
    if result.get("status") != 200:
        logger.error("MP payment fetch failed for %s: %s", data_id, result.get("response"))
        return {"status": "fetch_failed"}

    payment_data = result["response"]
    external_reference = payment_data.get("external_reference", "")
    mp_status = payment_data.get("status", "")

    if not external_reference:
        return {"status": "no_reference"}

    cycle = db.query(InstitutionBillingCycle).filter(
        InstitutionBillingCycle.id == external_reference
    ).first()
    if not cycle:
        return {"status": "cycle_not_found"}

    if mp_status == "approved":
        cycle.status = "paid"
        cycle.mp_payment_id = str(data_id)
        cycle.paid_at = datetime.now(UTC)
        db.commit()

    return {"status": "ok"}
