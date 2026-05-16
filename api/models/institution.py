import uuid
from datetime import datetime, UTC
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class InstitutionTenant(Base):
    __tablename__ = "institution_tenants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    vat_condition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_licenses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    used_licenses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class InstitutionTenantUnit(Base):
    __tablename__ = "institution_tenant_units"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    institution_tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institution_tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class InstitutionMember(Base):
    __tablename__ = "institution_members"
    __table_args__ = (
        UniqueConstraint("user_id", "institution_tenant_id", name="uq_member_user_tenant"),
        CheckConstraint("role IN ('admin', 'teacher')", name="ck_member_role"),
        CheckConstraint("status IN ('active', 'inactive')", name="ck_member_status"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(200), ForeignKey("users_profile.clerk_user_id"), nullable=False, index=True
    )
    institution_tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institution_tenants.id"), nullable=False, index=True
    )
    institution_unit_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("institution_tenant_units.id"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
