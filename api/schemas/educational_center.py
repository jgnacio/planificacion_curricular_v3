from datetime import datetime
from pydantic import BaseModel


class EducationalCenterCreate(BaseModel):
    name: str
    institution_tenant_id: str | None = None


class EducationalCenterUpdate(BaseModel):
    name: str | None = None
    institution_tenant_id: str | None = None


class EducationalCenterRead(BaseModel):
    id: str
    user_id: str
    name: str
    institution_tenant_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
