import uuid
from datetime import datetime, UTC
from decimal import Decimal
from sqlalchemy import (
    Boolean, CheckConstraint, ForeignKey, Integer,
    Numeric, String, DateTime, Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class MpPlan(Base):
    __tablename__ = "mp_plans"
    __table_args__ = (
        CheckConstraint("billing_period IN ('monthly', 'annual')", name="ck_mp_plan_period"),
        CheckConstraint("type IN ('individual', 'institutional')", name="ck_mp_plan_type"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    internal_code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mp_plan_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    unit_price_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    billing_period: Mapped[str] = mapped_column(String(20), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class IndividualSubscription(Base):
    __tablename__ = "individual_subscriptions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('authorized', 'paused', 'cancelled')", name="ck_sub_status"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(200), ForeignKey("users_profile.clerk_user_id"), nullable=False, index=True
    )
    mp_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("mp_plans.id"), nullable=False
    )
    mp_preapproval_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class License(Base):
    __tablename__ = "licenses"
    __table_args__ = (
        CheckConstraint(
            "status IN ('available', 'assigned', 'suspended')", name="ck_license_status"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    institution_tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institution_tenants.id"), nullable=False, index=True
    )
    assigned_to: Mapped[str | None] = mapped_column(
        String(200), ForeignKey("users_profile.clerk_user_id"), nullable=True
    )
    institution_unit_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("institution_tenant_units.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="available")
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class InstitutionBillingCycle(Base):
    __tablename__ = "institution_billing_cycles"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'paid', 'overdue', 'failed')", name="ck_billing_status"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    institution_tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institution_tenants.id"), nullable=False, index=True
    )
    mp_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("mp_plans.id"), nullable=False
    )
    license_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_amount_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    mp_preference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mp_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    institution_tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("institution_tenants.id"), nullable=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(200), ForeignKey("users_profile.clerk_user_id"), nullable=True
    )
    billing_cycle_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("institution_billing_cycles.id"), nullable=True
    )
    subscription_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("individual_subscriptions.id"), nullable=True
    )
    zsoft_cfe_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
