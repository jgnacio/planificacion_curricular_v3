import os

import mercadopago
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import UserContext, get_current_user
from api.database import get_db
from api.models.billing import IndividualSubscription, MpPlan
from api.models.user_profile import UserProfile
from api.schemas.subscription import CheckoutRequest, CheckoutResponse, MpPlanRead, SubscriptionRead

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _get_sdk() -> mercadopago.SDK:
    token = os.getenv("MP_ACCESS_TOKEN", "")
    if not token:
        raise HTTPException(status_code=500, detail="MP_ACCESS_TOKEN not configured")
    return mercadopago.SDK(token)


@router.get("/plans", response_model=list[MpPlanRead])
def list_plans(db: Session = Depends(get_db)):
    return db.query(MpPlan).filter(
        MpPlan.type == "individual",
        MpPlan.is_active == True,
    ).all()


@router.post("/checkout", response_model=CheckoutResponse, status_code=201)
def create_checkout(
    data: CheckoutRequest,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    active = db.query(IndividualSubscription).filter(
        IndividualSubscription.user_id == user.user_id,
        IndividualSubscription.status == "authorized",
    ).first()
    if active:
        raise HTTPException(status_code=409, detail="Active subscription already exists")

    plan = db.query(MpPlan).filter(
        MpPlan.internal_code == data.plan_internal_code,
        MpPlan.is_active == True,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    profile = db.query(UserProfile).filter(UserProfile.clerk_user_id == user.user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="User profile not found — complete your profile first")

    sdk = _get_sdk()
    preapproval_data = {
        "reason": plan.display_name,
        "payer_email": profile.email,
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months" if plan.billing_period == "monthly" else "years",
            "transaction_amount": float(plan.unit_price_usd),
            "currency_id": plan.currency,
        },
        "back_url": f"{os.getenv('FRONT_URL', 'http://localhost:3000')}/subscriptions",
        "notification_url": f"{os.getenv('BASE_URL', 'http://localhost:8000')}/webhooks/mp/individual",
        "status": "pending",
    }

    result = sdk.preapproval().create(preapproval_data)
    if result["status"] not in (200, 201):
        import logging
        logging.getLogger(__name__).error("MP preapproval failed: status=%s body=%s", result["status"], result.get("response"))
        raise HTTPException(status_code=502, detail=f"MP preapproval creation failed: {result.get('response')}")

    response_data = result["response"]
    return CheckoutResponse(
        init_point=response_data["init_point"],
        preapproval_id=response_data["id"],
    )


@router.get("/me", response_model=SubscriptionRead | None)
def get_my_subscription(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(IndividualSubscription).filter(
        IndividualSubscription.user_id == user.user_id,
        IndividualSubscription.status == "authorized",
    ).first()
