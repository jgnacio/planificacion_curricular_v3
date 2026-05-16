# pytest is NOT in requirements.txt — add it: pytest>=8.0
# httpx is present in api/requirements.txt (httpx==0.27.0)
#
# Run with:  pytest tests/test_integration.py -v
#
# SQLite FK enforcement is OFF by default — ForeignKey constraints are not
# checked at DB level in tests, which lets us create rows without parent deps
# and keeps seeding simple.

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import app and DB objects BEFORE creating the test engine so that all
# model metadata is registered on Base.
from api.main import app
from api.database import Base, get_db
from api.auth import get_current_user, UserContext
from api.models.billing import IndividualSubscription, License, MpPlan
from api.models.institution import InstitutionTenant
from api.models.user_profile import UserProfile

# ── Test DB setup ─────────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# ── Constants used across tests ───────────────────────────────────────────────

TENANT_ID = str(uuid.uuid4())
ADMIN_USER_ID = "admin_user_clerk_id"
OTHER_USER_ID = "other_user_clerk_id"
MP_PLAN_ID_EXTERNAL = "mp_ext_plan_001"  # mp_plans.mp_plan_id (MP side)


# ── Auth mock helpers ─────────────────────────────────────────────────────────

def _admin_user_context():
    return UserContext(
        user_id=ADMIN_USER_ID,
        role="institution_admin",
        institution_tenant_id=TENANT_ID,
    )


def _override_get_current_user_admin():
    async def _mock():
        return _admin_user_context()
    return _mock


# ── DB seed helpers ───────────────────────────────────────────────────────────

def _seed_tenant(db, tenant_id=TENANT_ID, total_licenses=2, used_licenses=0):
    tenant = InstitutionTenant(
        id=tenant_id,
        name="Test Institution",
        tax_id="12345678",
        email="admin@test.edu",
        total_licenses=total_licenses,
        used_licenses=used_licenses,
    )
    db.add(tenant)
    db.commit()
    return tenant


def _seed_license(db, tenant_id=TENANT_ID, status="available"):
    lic = License(
        id=str(uuid.uuid4()),
        institution_tenant_id=tenant_id,
        status=status,
    )
    db.add(lic)
    db.commit()
    db.refresh(lic)
    return lic


def _seed_user_profile(db, clerk_id=ADMIN_USER_ID):
    profile = UserProfile(
        clerk_user_id=clerk_id,
        email=f"{clerk_id}@test.com",
    )
    db.add(profile)
    db.commit()
    return profile


def _seed_mp_plan(db, mp_plan_id=MP_PLAN_ID_EXTERNAL):
    plan = MpPlan(
        id=str(uuid.uuid4()),
        internal_code=f"ind_monthly_{uuid.uuid4().hex[:6]}",
        display_name="Individual Monthly",
        mp_plan_id=mp_plan_id,
        currency="USD",
        unit_price_usd="9.99",
        billing_period="monthly",
        type="individual",
        is_active=True,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_db():
    """Wipe all tables before each test for isolation."""
    yield
    db = TestingSession()
    try:
        db.query(IndividualSubscription).delete()
        db.query(License).delete()
        db.query(MpPlan).delete()
        db.query(UserProfile).delete()
        db.query(InstitutionTenant).delete()
        db.commit()
    finally:
        db.close()


# ── Task 4.3 — License assignment tests ──────────────────────────────────────

class TestLicenseAssignment:

    def setup_method(self):
        app.dependency_overrides[get_current_user] = _override_get_current_user_admin()

    def teardown_method(self):
        app.dependency_overrides.pop(get_current_user, None)

    def test_assign_license_success(self):
        db = TestingSession()
        try:
            _seed_tenant(db, total_licenses=2, used_licenses=0)
            lic = _seed_license(db, status="available")
        finally:
            db.close()

        resp = client.post(
            f"/institutions/{TENANT_ID}/licenses/{lic.id}/assign",
            json={"user_id": OTHER_USER_ID},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "assigned"
        assert body["assigned_to"] == OTHER_USER_ID

    def test_assign_license_already_assigned(self):
        """Assigning a license that is already 'assigned' → 404 (not found/available)."""
        db = TestingSession()
        try:
            _seed_tenant(db, total_licenses=2, used_licenses=1)
            lic = _seed_license(db, status="assigned")
        finally:
            db.close()

        resp = client.post(
            f"/institutions/{TENANT_ID}/licenses/{lic.id}/assign",
            json={"user_id": OTHER_USER_ID},
        )
        # The endpoint filters status == "available", so already-assigned → 404
        assert resp.status_code == 404

    def test_assign_license_limit_exceeded(self):
        """used_licenses >= total_licenses → 422 before even touching the license."""
        db = TestingSession()
        try:
            _seed_tenant(db, total_licenses=2, used_licenses=2)
            lic = _seed_license(db, status="available")
        finally:
            db.close()

        resp = client.post(
            f"/institutions/{TENANT_ID}/licenses/{lic.id}/assign",
            json={"user_id": OTHER_USER_ID},
        )
        assert resp.status_code == 422
        assert "no available licenses" in resp.json()["detail"]

    def test_assign_license_updates_used_count(self):
        """After assignment, institution.used_licenses is incremented by 1."""
        db = TestingSession()
        try:
            _seed_tenant(db, total_licenses=2, used_licenses=0)
            lic = _seed_license(db, status="available")
        finally:
            db.close()

        client.post(
            f"/institutions/{TENANT_ID}/licenses/{lic.id}/assign",
            json={"user_id": OTHER_USER_ID},
        )

        db = TestingSession()
        try:
            tenant = db.query(InstitutionTenant).filter_by(id=TENANT_ID).first()
            assert tenant.used_licenses == 1
        finally:
            db.close()

    def test_assign_license_wrong_tenant(self):
        """Admin of tenant A cannot assign a license belonging to tenant B."""
        other_tenant_id = str(uuid.uuid4())
        db = TestingSession()
        try:
            _seed_tenant(db, total_licenses=2, used_licenses=0)
            other_tenant = InstitutionTenant(
                id=other_tenant_id,
                name="Other Inst",
                tax_id="99999999",
                email="other@test.edu",
                total_licenses=2,
                used_licenses=0,
            )
            db.add(other_tenant)
            db.commit()
            lic = _seed_license(db, tenant_id=other_tenant_id, status="available")
        finally:
            db.close()

        resp = client.post(
            f"/institutions/{other_tenant_id}/licenses/{lic.id}/assign",
            json={"user_id": OTHER_USER_ID},
        )
        # User's institution_tenant_id != other_tenant_id → 403
        assert resp.status_code == 403


# ── Task 4.4 — MP webhook → IndividualSubscription ───────────────────────────

class TestMpWebhook:

    def test_webhook_creates_subscription_on_authorized(self):
        db = TestingSession()
        try:
            _seed_user_profile(db, clerk_id=OTHER_USER_ID)
            plan = _seed_mp_plan(db)
        finally:
            db.close()

        preapproval_id = f"preapproval_{uuid.uuid4().hex}"
        payload = {
            "type": "subscription_preapproval",
            "data": {
                "id": preapproval_id,
                "status": "authorized",
                "payer_id": OTHER_USER_ID,
                "preapproval_plan_id": MP_PLAN_ID_EXTERNAL,
            },
        }

        resp = client.post("/webhooks/mp/individual", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        db = TestingSession()
        try:
            sub = db.query(IndividualSubscription).filter_by(
                mp_preapproval_id=preapproval_id
            ).first()
            assert sub is not None
            assert sub.status == "authorized"
            assert sub.user_id == OTHER_USER_ID
        finally:
            db.close()

    def test_webhook_ignored_for_unknown_type(self):
        payload = {
            "type": "payment",
            "data": {"id": "pay-123", "status": "approved"},
        }
        resp = client.post("/webhooks/mp/individual", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_webhook_updates_existing_subscription_to_cancelled(self):
        db = TestingSession()
        try:
            _seed_user_profile(db, clerk_id=OTHER_USER_ID)
            plan = _seed_mp_plan(db)
            preapproval_id = f"preapproval_{uuid.uuid4().hex}"
            sub = IndividualSubscription(
                user_id=OTHER_USER_ID,
                mp_plan_id=plan.id,
                mp_preapproval_id=preapproval_id,
                status="authorized",
            )
            db.add(sub)
            db.commit()
        finally:
            db.close()

        cancel_payload = {
            "type": "subscription_preapproval",
            "data": {
                "id": preapproval_id,
                "status": "cancelled",
                "payer_id": OTHER_USER_ID,
                "preapproval_plan_id": MP_PLAN_ID_EXTERNAL,
            },
        }
        resp = client.post("/webhooks/mp/individual", json=cancel_payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        db = TestingSession()
        try:
            sub = db.query(IndividualSubscription).filter_by(
                mp_preapproval_id=preapproval_id
            ).first()
            assert sub.status == "cancelled"
            assert sub.canceled_at is not None
        finally:
            db.close()

    def test_webhook_no_id_in_data(self):
        payload = {
            "type": "subscription_preapproval",
            "data": {"status": "authorized"},
        }
        resp = client.post("/webhooks/mp/individual", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "no_id"

    def test_webhook_no_matching_plan_does_not_create_subscription(self):
        """If preapproval_plan_id doesn't match any MpPlan, no subscription is created."""
        db = TestingSession()
        try:
            _seed_user_profile(db, clerk_id=OTHER_USER_ID)
        finally:
            db.close()

        preapproval_id = f"preapproval_{uuid.uuid4().hex}"
        payload = {
            "type": "subscription_preapproval",
            "data": {
                "id": preapproval_id,
                "status": "authorized",
                "payer_id": OTHER_USER_ID,
                "preapproval_plan_id": "nonexistent-plan",
            },
        }
        resp = client.post("/webhooks/mp/individual", json=payload)
        assert resp.status_code == 200

        db = TestingSession()
        try:
            sub = db.query(IndividualSubscription).filter_by(
                mp_preapproval_id=preapproval_id
            ).first()
            assert sub is None
        finally:
            db.close()

    def test_webhook_signature_verification_rejects_bad_sig(self):
        """When MP_SECRET_KEY is set, invalid signature → 401."""
        with patch("api.routes.webhooks.MP_SECRET_KEY", "real-secret"):
            resp = client.post(
                "/webhooks/mp/individual",
                json={"type": "subscription_preapproval", "data": {"id": "x"}},
                headers={
                    "x-signature": "ts=1234,v1=badhash",
                    "x-request-id": "req-bad",
                },
            )
        assert resp.status_code == 401
