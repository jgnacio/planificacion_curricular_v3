# pytest is NOT in requirements.txt — add it: pytest>=8.0
# httpx is present in api/requirements.txt (httpx==0.27.0)

import asyncio
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from api.auth import UserContext, get_current_user, require_institution_admin


def _run(coro):
    return asyncio.run(coro)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_payload(sub="user_abc", role="institution_admin", tenant_id="tenant-123"):
    payload = {"sub": sub}
    if role is not None or tenant_id is not None:
        payload["public_metadata"] = {}
        if role is not None:
            payload["public_metadata"]["role"] = role
        if tenant_id is not None:
            payload["public_metadata"]["institution_tenant_id"] = tenant_id
    return payload


# ── get_current_user ──────────────────────────────────────────────────────────

def test_get_current_user_valid_jwt():
    payload = _make_payload()
    with patch("api.auth._decode_token", return_value=payload):
        user = _run(get_current_user(authorization="Bearer fake.token.here"))
    assert user.user_id == "user_abc"
    assert user.role == "institution_admin"
    assert user.institution_tenant_id == "tenant-123"


def test_get_current_user_missing_metadata():
    payload = {"sub": "user_xyz"}
    with patch("api.auth._decode_token", return_value=payload):
        user = _run(get_current_user(authorization="Bearer fake.token.here"))
    assert user.user_id == "user_xyz"
    assert user.role is None
    assert user.institution_tenant_id is None


def test_get_current_user_partial_metadata():
    payload = {"sub": "user_partial", "public_metadata": {"role": "teacher"}}
    with patch("api.auth._decode_token", return_value=payload):
        user = _run(get_current_user(authorization="Bearer fake.token.here"))
    assert user.role == "teacher"
    assert user.institution_tenant_id is None


def test_get_current_user_no_authorization():
    with pytest.raises(HTTPException) as exc:
        _run(get_current_user(authorization=None))
    assert exc.value.status_code == 401


def test_get_current_user_malformed_bearer():
    with pytest.raises(HTTPException) as exc:
        _run(get_current_user(authorization="NotBearer token"))
    assert exc.value.status_code == 401


def test_get_current_user_internal_key():
    with patch("api.auth.INTERNAL_API_KEY", "secret-key"):
        user = _run(get_current_user(x_internal_key="secret-key", user_id="internal-user-99"))
    assert user.user_id == "internal-user-99"
    assert user.role is None
    assert user.institution_tenant_id is None


def test_get_current_user_internal_key_missing_user_id():
    with patch("api.auth.INTERNAL_API_KEY", "secret-key"):
        with pytest.raises(HTTPException) as exc:
            _run(get_current_user(x_internal_key="secret-key", user_id=None))
    assert exc.value.status_code == 400


# ── require_institution_admin ─────────────────────────────────────────────────

def test_require_institution_admin_correct_role():
    user = UserContext(
        user_id="u1",
        role="institution_admin",
        institution_tenant_id="tenant-abc",
    )
    result = require_institution_admin(user)
    assert result is user


def test_require_institution_admin_wrong_role():
    user = UserContext(user_id="u2", role="teacher", institution_tenant_id="tenant-abc")
    with pytest.raises(HTTPException) as exc:
        require_institution_admin(user)
    assert exc.value.status_code == 403


def test_require_institution_admin_no_role():
    user = UserContext(user_id="u3", role=None, institution_tenant_id="tenant-abc")
    with pytest.raises(HTTPException) as exc:
        require_institution_admin(user)
    assert exc.value.status_code == 403


def test_require_institution_admin_no_tenant_id():
    """Even with correct role, missing tenant_id must raise 403."""
    user = UserContext(user_id="u4", role="institution_admin", institution_tenant_id=None)
    with pytest.raises(HTTPException) as exc:
        require_institution_admin(user)
    assert exc.value.status_code == 403


def test_require_institution_admin_both_missing():
    user = UserContext(user_id="u5", role=None, institution_tenant_id=None)
    with pytest.raises(HTTPException) as exc:
        require_institution_admin(user)
    assert exc.value.status_code == 403
