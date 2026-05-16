from datetime import datetime
from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    plan_internal_code: str


class CheckoutResponse(BaseModel):
    init_point: str
    preapproval_id: str


class SubscriptionRead(BaseModel):
    id: str
    user_id: str
    mp_plan_id: str
    mp_preapproval_id: str
    status: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    canceled_at: datetime | None

    model_config = {"from_attributes": True}


class MpPlanRead(BaseModel):
    id: str
    internal_code: str
    display_name: str
    currency: str
    unit_price_usd: float
    billing_period: str
    type: str

    model_config = {"from_attributes": True}
