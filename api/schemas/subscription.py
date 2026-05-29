from datetime import datetime
from pydantic import BaseModel, Field


class CheckoutRequest(BaseModel):
    plan_id: str | None = None
    plan_internal_code: str | None = None


class CheckoutResponse(BaseModel):
    init_point: str
    preapproval_id: str


class SubscriptionRead(BaseModel):
    id: str
    plan_name: str
    status: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    canceled_at: datetime | None = None

    model_config = {"from_attributes": True}


class MpPlanRead(BaseModel):
    id: str
    name: str = Field(validation_alias="display_name")
    description: str | None = None
    price_usd: float = Field(validation_alias="unit_price_usd")
    billing_period: str
    currency: str
    mp_plan_id: str | None = None
    internal_code: str

    model_config = {"from_attributes": True, "populate_by_name": True}


class PlanSyncResponse(BaseModel):
    mp_plan_id: str
    init_point: str | None = None
