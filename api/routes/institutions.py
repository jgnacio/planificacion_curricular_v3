from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import UserContext, get_current_user, require_institution_admin
from api.database import get_db
from api.models.billing import License
from api.models.institution import InstitutionMember, InstitutionTenant, InstitutionTenantUnit
from api.schemas.institution import (
    InstitutionMemberCreate,
    InstitutionMemberRead,
    InstitutionTenantCreate,
    InstitutionTenantRead,
    InstitutionTenantUpdate,
    InstitutionUnitCreate,
    InstitutionUnitRead,
    LicenseAssign,
    LicensePoolCreate,
    LicenseRead,
)

router = APIRouter(prefix="/institutions", tags=["institutions"])


# ── Institution Tenants ──────────────────────────────────────────────────────

@router.post("/", response_model=InstitutionTenantRead, status_code=201)
def create_institution(
    data: InstitutionTenantCreate,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    inst = InstitutionTenant(**data.model_dump())
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


@router.get("/", response_model=list[InstitutionTenantRead])
def list_institutions(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    return db.query(InstitutionTenant).filter(
        InstitutionTenant.id == user.institution_tenant_id
    ).all()


@router.get("/{institution_id}", response_model=InstitutionTenantRead)
def get_institution(
    institution_id: str,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    inst = _get_tenant_or_404(institution_id, user, db)
    return inst


@router.patch("/{institution_id}", response_model=InstitutionTenantRead)
def update_institution(
    institution_id: str,
    data: InstitutionTenantUpdate,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    inst = _get_tenant_or_404(institution_id, user, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(inst, field, value)
    db.commit()
    db.refresh(inst)
    return inst


# ── Units ────────────────────────────────────────────────────────────────────

@router.post("/{institution_id}/units", response_model=InstitutionUnitRead, status_code=201)
def create_unit(
    institution_id: str,
    data: InstitutionUnitCreate,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    _get_tenant_or_404(institution_id, user, db)
    unit = InstitutionTenantUnit(**data.model_dump(), institution_tenant_id=institution_id)
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@router.get("/{institution_id}/units", response_model=list[InstitutionUnitRead])
def list_units(
    institution_id: str,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    _get_tenant_or_404(institution_id, user, db)
    return db.query(InstitutionTenantUnit).filter(
        InstitutionTenantUnit.institution_tenant_id == institution_id
    ).all()


# ── Members ──────────────────────────────────────────────────────────────────

@router.post("/{institution_id}/members", response_model=InstitutionMemberRead, status_code=201)
def add_member(
    institution_id: str,
    data: InstitutionMemberCreate,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    _get_tenant_or_404(institution_id, user, db)
    member = InstitutionMember(**data.model_dump(), institution_tenant_id=institution_id)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("/{institution_id}/members", response_model=list[InstitutionMemberRead])
def list_members(
    institution_id: str,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    _get_tenant_or_404(institution_id, user, db)
    return db.query(InstitutionMember).filter(
        InstitutionMember.institution_tenant_id == institution_id
    ).all()


# ── Licenses ─────────────────────────────────────────────────────────────────

@router.post("/{institution_id}/licenses", response_model=list[LicenseRead], status_code=201)
def create_license_pool(
    institution_id: str,
    data: LicensePoolCreate,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    inst = _get_tenant_or_404(institution_id, user, db)
    licenses = [
        License(institution_tenant_id=institution_id)
        for _ in range(data.quantity)
    ]
    db.add_all(licenses)
    inst.total_licenses += data.quantity
    db.commit()
    for lic in licenses:
        db.refresh(lic)
    return licenses


@router.get("/{institution_id}/licenses", response_model=list[LicenseRead])
def list_licenses(
    institution_id: str,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    _get_tenant_or_404(institution_id, user, db)
    return db.query(License).filter(
        License.institution_tenant_id == institution_id
    ).all()


@router.post("/{institution_id}/licenses/{license_id}/assign", response_model=LicenseRead)
def assign_license(
    institution_id: str,
    license_id: str,
    data: LicenseAssign,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    inst = _get_tenant_or_404(institution_id, user, db)

    if inst.used_licenses >= inst.total_licenses:
        raise HTTPException(status_code=422, detail="no available licenses")

    lic = db.query(License).filter(
        License.id == license_id,
        License.institution_tenant_id == institution_id,
        License.status == "available",
    ).first()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found or not available")

    lic.assigned_to = data.user_id
    lic.institution_unit_id = data.institution_unit_id
    lic.status = "assigned"
    lic.assigned_at = datetime.now(UTC)
    lic.released_at = None
    inst.used_licenses += 1
    db.commit()
    db.refresh(lic)
    return lic


@router.delete("/{institution_id}/licenses/{license_id}/assign", response_model=LicenseRead)
def revoke_license(
    institution_id: str,
    license_id: str,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_institution_admin(user)
    inst = _get_tenant_or_404(institution_id, user, db)

    lic = db.query(License).filter(
        License.id == license_id,
        License.institution_tenant_id == institution_id,
        License.status == "assigned",
    ).first()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found or not assigned")

    lic.assigned_to = None
    lic.institution_unit_id = None
    lic.status = "available"
    lic.released_at = datetime.now(UTC)
    inst.used_licenses = max(0, inst.used_licenses - 1)
    db.commit()
    db.refresh(lic)
    return lic


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_tenant_or_404(institution_id: str, user: UserContext, db: Session) -> InstitutionTenant:
    if institution_id != user.institution_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    inst = db.query(InstitutionTenant).filter(InstitutionTenant.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    return inst
