from datetime import datetime
from pydantic import BaseModel


class InstitutionTenantCreate(BaseModel):
    name: str
    tax_id: str
    address: str | None = None
    state: str | None = None
    phone: str | None = None
    email: str
    vat_condition: str | None = None


class InstitutionTenantUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    state: str | None = None
    phone: str | None = None
    email: str | None = None
    vat_condition: str | None = None


class InstitutionTenantRead(BaseModel):
    id: str
    name: str
    tax_id: str
    address: str | None
    state: str | None
    phone: str | None
    email: str
    vat_condition: str | None
    total_licenses: int
    used_licenses: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InstitutionUnitCreate(BaseModel):
    name: str
    address: str | None = None


class InstitutionUnitRead(BaseModel):
    id: str
    institution_tenant_id: str
    name: str
    address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InstitutionMemberCreate(BaseModel):
    user_id: str
    role: str
    institution_unit_id: str | None = None


class InstitutionMemberRead(BaseModel):
    id: str
    user_id: str
    institution_tenant_id: str
    institution_unit_id: str | None
    role: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LicensePoolCreate(BaseModel):
    quantity: int
    mp_plan_id: str


class LicenseRead(BaseModel):
    id: str
    institution_tenant_id: str
    assigned_to: str | None
    institution_unit_id: str | None
    status: str
    assigned_at: datetime | None
    released_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LicenseAssign(BaseModel):
    user_id: str
    institution_unit_id: str | None = None
