import logging
import os
from datetime import datetime, UTC
from urllib.parse import urlencode

import mercadopago
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import UserContext, get_current_user, require_institution_admin
from api.database import get_db
from api.models.billing import IndividualSubscription, MpPlan
from api.models.user_profile import UserProfile
from api.schemas.subscription import (
    CheckoutRequest,
    CheckoutResponse,
    MpPlanRead,
    PlanSyncResponse,
    SubscriptionRead,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _get_sdk() -> mercadopago.SDK:
    token = os.getenv("MP_ACCESS_TOKEN", "")
    if not token:
        raise HTTPException(status_code=500, detail="MP_ACCESS_TOKEN not configured")
    return mercadopago.SDK(token)


def _subscription_to_read(sub: IndividualSubscription, plan: MpPlan | None) -> SubscriptionRead:
    return SubscriptionRead(
        id=sub.id,
        plan_name=plan.display_name if plan else "Plan",
        status=sub.status,
        period_start=sub.current_period_start,
        period_end=sub.current_period_end,
        canceled_at=sub.canceled_at,
    )


@router.get("/plans", response_model=list[MpPlanRead])
def list_plans(db: Session = Depends(get_db)) -> list[MpPlan]:
    return db.query(MpPlan).filter(
        MpPlan.type == "individual",
        MpPlan.is_active == True,  # noqa: E712
    ).all()


@router.get("/active", response_model=SubscriptionRead | None)
def get_active_subscription(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionRead | None:
    sub = db.query(IndividualSubscription).filter(
        IndividualSubscription.user_id == user.user_id,
        IndividualSubscription.status == "authorized",
    ).first()
    if not sub:
        return None
    plan = db.query(MpPlan).filter(MpPlan.id == sub.mp_plan_id).first()
    return _subscription_to_read(sub, plan)


@router.get("/me", response_model=SubscriptionRead | None)
def get_my_subscription(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionRead | None:
    return get_active_subscription(user=user, db=db)


@router.post("/checkout", response_model=CheckoutResponse, status_code=201)
def create_checkout(
    data: CheckoutRequest,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    active = db.query(IndividualSubscription).filter(
        IndividualSubscription.user_id == user.user_id,
        IndividualSubscription.status == "authorized",
    ).first()
    if active:
        raise HTTPException(status_code=409, detail="Active subscription already exists")

    plan_query = db.query(MpPlan).filter(MpPlan.is_active == True)  # noqa: E712
    if data.plan_id:
        plan = plan_query.filter(MpPlan.id == data.plan_id).first()
    elif data.plan_internal_code:
        plan = plan_query.filter(MpPlan.internal_code == data.plan_internal_code).first()
    else:
        raise HTTPException(status_code=400, detail="plan_id or plan_internal_code required")

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if not plan.mp_plan_id:
        raise HTTPException(
            status_code=409,
            detail="Plan not synced to Mercado Pago — admin must sync it first",
        )

    # Crear preapproval server-side con external_reference para que el webhook identifique al usuario.
    # URL params no funcionan — MP no los propaga al preapproval. Server-side sí.
    front_url = os.getenv("FRONT_URL", "https://app.facilitadordocente.com")
    sdk = _get_sdk()
    preapproval_data = {
        "preapproval_plan_id": plan.mp_plan_id,
        "reason": plan.display_name,
        "external_reference": user.user_id,
        "back_url": f"{front_url}/subscriptions/success",
        "status": "pending",
    }
    result = sdk.subscription().create(preapproval_data)

    if result.get("status") not in (200, 201):
        # Fallback: redirect al hosted checkout del plan
        logger.warning("Server-side preapproval failed (%s), fallback to hosted checkout", result.get("status"))
        plan_result = sdk.plan().get(plan.mp_plan_id)
        mp_plan_data = plan_result.get("response", {})
        token = os.getenv("MP_ACCESS_TOKEN", "")
        is_test = token.startswith("TEST-")
        init_point: str = (
            mp_plan_data.get("sandbox_init_point", "") if is_test
            else mp_plan_data.get("init_point", "")
        ) or mp_plan_data.get("init_point", "")
        if not init_point:
            params = urlencode({"preapproval_plan_id": plan.mp_plan_id, "external_reference": user.user_id})
            init_point = f"https://www.mercadopago.com/subscriptions/checkout?{params}"
        else:
            sep = "&" if "?" in init_point else "?"
            init_point = f"{init_point}{sep}external_reference={user.user_id}"
        return CheckoutResponse(init_point=init_point, preapproval_id="")

    response = result["response"]
    return CheckoutResponse(init_point=response["init_point"], preapproval_id=response["id"])


def _update_mp_status(preapproval_id: str, new_status: str) -> None:
    sdk = _get_sdk()
    result = sdk.subscription().update(preapproval_id, {"status": new_status})
    if result["status"] not in (200, 201):
        logger.error("MP update failed: %s", result.get("response"))
        raise HTTPException(status_code=502, detail=f"MP {new_status} failed")


@router.put("/me/cancel", response_model=SubscriptionRead)
def cancel_my_subscription(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionRead:
    sub = db.query(IndividualSubscription).filter(
        IndividualSubscription.user_id == user.user_id,
        IndividualSubscription.status.in_(["authorized", "paused"]),
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")

    _update_mp_status(sub.mp_preapproval_id, "cancelled")
    sub.status = "cancelled"
    sub.canceled_at = datetime.now(UTC)
    db.commit()

    plan = db.query(MpPlan).filter(MpPlan.id == sub.mp_plan_id).first()
    return _subscription_to_read(sub, plan)


@router.put("/me/pause", response_model=SubscriptionRead)
def pause_my_subscription(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionRead:
    sub = db.query(IndividualSubscription).filter(
        IndividualSubscription.user_id == user.user_id,
        IndividualSubscription.status == "authorized",
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")

    _update_mp_status(sub.mp_preapproval_id, "paused")
    sub.status = "paused"
    db.commit()

    plan = db.query(MpPlan).filter(MpPlan.id == sub.mp_plan_id).first()
    return _subscription_to_read(sub, plan)


@router.put("/me/reactivate", response_model=SubscriptionRead)
def reactivate_my_subscription(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionRead:
    sub = db.query(IndividualSubscription).filter(
        IndividualSubscription.user_id == user.user_id,
        IndividualSubscription.status == "paused",
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="No paused subscription")

    _update_mp_status(sub.mp_preapproval_id, "authorized")
    sub.status = "authorized"
    db.commit()

    plan = db.query(MpPlan).filter(MpPlan.id == sub.mp_plan_id).first()
    return _subscription_to_read(sub, plan)


@router.post("/admin/plans/{plan_id}/sync", response_model=PlanSyncResponse)
def sync_plan_to_mp(
    plan_id: str,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanSyncResponse:
    require_institution_admin(user)

    plan = db.query(MpPlan).filter(MpPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.mp_plan_id:
        raise HTTPException(status_code=409, detail="Plan already synced")

    # MP no soporta "years" — anual = 12 months
    if plan.billing_period == "monthly":
        frequency, frequency_type = 1, "months"
    elif plan.billing_period == "annual":
        frequency, frequency_type = 12, "months"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported billing_period: {plan.billing_period}")

    sdk = _get_sdk()
    plan_data = {
        "reason": plan.display_name,
        "auto_recurring": {
            "frequency": frequency,
            "frequency_type": frequency_type,
            "transaction_amount": float(plan.unit_price_usd),
            "currency_id": plan.currency,
        },
        "back_url": f"{os.getenv('FRONT_URL', 'http://localhost:3000')}/subscriptions/success",
        "status": "active",
    }
    result = sdk.plan().create(plan_data)
    if result["status"] not in (200, 201):
        logger.error("MP plan create failed: %s", result.get("response"))
        raise HTTPException(status_code=502, detail=f"MP plan creation failed: {result.get('response')}")

    response = result["response"]
    plan.mp_plan_id = response["id"]
    db.commit()

    return PlanSyncResponse(
        mp_plan_id=response["id"],
        init_point=response.get("init_point"),
    )
