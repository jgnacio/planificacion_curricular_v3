from datetime import datetime
from pydantic import BaseModel


class BillingCycleCreate(BaseModel):
    mp_plan_id: str


class BillingCycleRead(BaseModel):
    id: str
    institution_tenant_id: str
    mp_plan_id: str
    license_count: int
    unit_price_usd: float
    total_amount_usd: float
    period_start: datetime
    period_end: datetime
    due_date: datetime
    mp_preference_id: str | None
    mp_payment_id: str | None
    status: str
    paid_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingCycleCheckoutResponse(BaseModel):
    cycle_id: str
    checkout_url: str
    total_amount_usd: float
    license_count: int
