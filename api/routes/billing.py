import os
from datetime import datetime, timedelta, UTC

import mercadopago
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import UserContext, get_current_user, require_institution_admin
from api.database import get_db
from api.models.billing import InstitutionBillingCycle, License, MpPlan
from api.models.institution import InstitutionTenant
from api.schemas.billing import BillingCycleCheckoutResponse, BillingCycleCreate, BillingCycleRead

router = APIRouter(prefix="/institutions", tags=["billing"])

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
FRONT_URL = os.getenv("FRONT_URL", "http://localhost:3000")


def _get_sdk() -> mercadopago.SDK:
    if not MP_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MP_ACCESS_TOKEN not configured")
    return mercadopago.SDK(MP_ACCESS_TOKEN)


@router.post("/{institution_id}/billing/cycle", response_model=BillingCycleCheckoutResponse, status_code=201)
def create_billing_cycle(
    institution_id: str,
    data: BillingCycleCreate,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    if institution_id != user.institution_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    inst = db.query(InstitutionTenant).filter(InstitutionTenant.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    plan = db.query(MpPlan).filter(
        MpPlan.id == data.mp_plan_id,
        MpPlan.type == "institutional",
        MpPlan.is_active == True,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Institutional plan not found")

    license_count = db.query(License).filter(
        License.institution_tenant_id == institution_id,
        License.status == "assigned",
    ).count()

    if license_count == 0:
        raise HTTPException(status_code=422, detail="No assigned licenses to bill")

    total = float(plan.unit_price_usd) * license_count
    now = datetime.now(UTC)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    due_date = period_start + timedelta(days=10)

    cycle = InstitutionBillingCycle(
        institution_tenant_id=institution_id,
        mp_plan_id=plan.id,
        license_count=license_count,
        unit_price_usd=plan.unit_price_usd,
        total_amount_usd=total,
        period_start=period_start,
        period_end=period_end,
        due_date=due_date,
    )
    db.add(cycle)
    db.flush()

    sdk = _get_sdk()
    preference_data = {
        "items": [{
            "title": f"Licencias {inst.name} — {period_start.strftime('%Y-%m')}",
            "quantity": license_count,
            "unit_price": float(plan.unit_price_usd),
            "currency_id": plan.currency,
        }],
        "notification_url": f"{BASE_URL}/webhooks/mp/institutional",
        "back_urls": {
            "success": f"{FRONT_URL}/admin/billing",
            "failure": f"{FRONT_URL}/admin/billing",
            "pending": f"{FRONT_URL}/admin/billing",
        },
        "external_reference": cycle.id,
    }

    result = sdk.preference().create(preference_data)
    if result["status"] not in (200, 201):
        db.rollback()
        raise HTTPException(status_code=502, detail="MP preference creation failed")

    cycle.mp_preference_id = result["response"]["id"]
    db.commit()
    db.refresh(cycle)

    return BillingCycleCheckoutResponse(
        cycle_id=cycle.id,
        checkout_url=result["response"]["init_point"],
        total_amount_usd=total,
        license_count=license_count,
    )


@router.get("/{institution_id}/billing/cycles", response_model=list[BillingCycleRead])
def list_billing_cycles(
    institution_id: str,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    if institution_id != user.institution_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return db.query(InstitutionBillingCycle).filter(
        InstitutionBillingCycle.institution_tenant_id == institution_id
    ).order_by(InstitutionBillingCycle.created_at.desc()).all()
