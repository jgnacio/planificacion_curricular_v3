import hashlib
import hmac
import os
from datetime import datetime, UTC

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi import Depends

from api.database import get_db
from api.models.billing import IndividualSubscription, InstitutionBillingCycle, MpPlan

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

MP_SECRET_KEY = os.getenv("MP_SECRET_KEY", "")


def _verify_mp_signature(x_signature: str, x_request_id: str, body: bytes) -> bool:
    if not MP_SECRET_KEY:
        return False
    try:
        parts = dict(p.split("=", 1) for p in x_signature.split(","))
        ts = parts.get("ts", "")
        v1 = parts.get("v1", "")
        manifest = f"id:{x_request_id};ts:{ts};"
        expected = hmac.new(
            MP_SECRET_KEY.encode(),
            manifest.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, v1)
    except Exception:
        return False


@router.post("/mp/individual")
async def mp_individual_webhook(
    request: Request,
    x_signature: str | None = Header(None),
    x_request_id: str | None = Header(None),
    db: Session = Depends(get_db),
):
    body = await request.body()

    if MP_SECRET_KEY and x_signature and x_request_id:
        if not _verify_mp_signature(x_signature, x_request_id, body):
            raise HTTPException(status_code=401, detail="Invalid MP signature")

    payload = await request.json() if not body else __import__("json").loads(body)
    event_type = payload.get("type")

    if event_type not in ("subscription_preapproval",):
        return {"status": "ignored"}

    data = payload.get("data", {})
    preapproval_id = data.get("id")
    if not preapproval_id:
        return {"status": "no_id"}

    mp_status = payload.get("data", {}).get("status", "")

    sub = db.query(IndividualSubscription).filter(
        IndividualSubscription.mp_preapproval_id == preapproval_id
    ).first()

    if sub:
        sub.status = mp_status
        if mp_status == "cancelled":
            sub.canceled_at = datetime.now(UTC)
    else:
        user_id = payload.get("data", {}).get("payer_id", "")
        plan = db.query(MpPlan).filter(
            MpPlan.mp_plan_id == payload.get("data", {}).get("preapproval_plan_id")
        ).first()
        if plan and user_id and mp_status == "authorized":
            sub = IndividualSubscription(
                user_id=user_id,
                mp_plan_id=plan.id,
                mp_preapproval_id=preapproval_id,
                status=mp_status,
                current_period_start=datetime.now(UTC),
            )
            db.add(sub)

    db.commit()
    return {"status": "ok"}


@router.post("/mp/institutional")
async def mp_institutional_webhook(
    request: Request,
    x_signature: str | None = Header(None),
    x_request_id: str | None = Header(None),
    db: Session = Depends(get_db),
):
    body = await request.body()

    if MP_SECRET_KEY and x_signature and x_request_id:
        if not _verify_mp_signature(x_signature, x_request_id, body):
            raise HTTPException(status_code=401, detail="Invalid MP signature")

    payload = __import__("json").loads(body) if body else {}
    event_type = payload.get("type")

    if event_type != "payment":
        return {"status": "ignored"}

    data = payload.get("data", {})
    payment_id = str(data.get("id", ""))
    external_reference = data.get("external_reference", "")

    if not external_reference:
        return {"status": "no_reference"}

    cycle = db.query(InstitutionBillingCycle).filter(
        InstitutionBillingCycle.id == external_reference
    ).first()
    if not cycle:
        return {"status": "cycle_not_found"}

    mp_status = data.get("status", "")
    if mp_status == "approved":
        cycle.status = "paid"
        cycle.mp_payment_id = payment_id
        cycle.paid_at = datetime.now(UTC)
        db.commit()

    return {"status": "ok"}
