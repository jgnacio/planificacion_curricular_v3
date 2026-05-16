# pytest is NOT in requirements.txt — add it: pytest>=8.0
# httpx is present in api/requirements.txt (httpx==0.27.0)

import hashlib
import hmac
import os
from unittest.mock import patch

import pytest

from api.routes.webhooks import _verify_mp_signature


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_signature(secret: str, request_id: str, ts: str = "1700000000") -> str:
    """Build a valid x-signature string matching _verify_mp_signature logic."""
    manifest = f"id:{request_id};ts:{ts};"
    v1 = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f"ts={ts},v1={v1}"


# ── _verify_mp_signature ──────────────────────────────────────────────────────

def test_verify_mp_signature_valid():
    secret = "test-secret-key"
    request_id = "req-001"
    sig = _build_signature(secret, request_id)

    with patch("api.routes.webhooks.MP_SECRET_KEY", secret):
        result = _verify_mp_signature(sig, request_id, b"irrelevant-body")

    assert result is True


def test_verify_mp_signature_wrong_secret():
    correct_secret = "correct-secret"
    wrong_secret = "wrong-secret"
    request_id = "req-002"
    sig = _build_signature(correct_secret, request_id)

    with patch("api.routes.webhooks.MP_SECRET_KEY", wrong_secret):
        result = _verify_mp_signature(sig, request_id, b"body")

    assert result is False


def test_verify_mp_signature_tampered_v1():
    secret = "my-secret"
    request_id = "req-003"
    ts = "1700000000"
    sig = f"ts={ts},v1=deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"

    with patch("api.routes.webhooks.MP_SECRET_KEY", secret):
        result = _verify_mp_signature(sig, request_id, b"body")

    assert result is False


def test_verify_mp_signature_malformed_no_v1():
    """x_signature missing v1= part → KeyError caught → False."""
    with patch("api.routes.webhooks.MP_SECRET_KEY", "any-secret"):
        result = _verify_mp_signature("ts=1234567890", "req-004", b"body")

    assert result is False


def test_verify_mp_signature_empty_string():
    with patch("api.routes.webhooks.MP_SECRET_KEY", "any-secret"):
        result = _verify_mp_signature("", "req-005", b"body")

    assert result is False


def test_verify_mp_signature_empty_mp_secret():
    """When MP_SECRET_KEY is empty, must return False regardless."""
    secret = "valid-secret"
    request_id = "req-006"
    sig = _build_signature(secret, request_id)

    with patch("api.routes.webhooks.MP_SECRET_KEY", ""):
        result = _verify_mp_signature(sig, request_id, b"body")

    assert result is False


def test_verify_mp_signature_wrong_request_id():
    """Valid signature for request_id A must fail when checked against request_id B."""
    secret = "secret"
    sig = _build_signature(secret, "req-A")

    with patch("api.routes.webhooks.MP_SECRET_KEY", secret):
        result = _verify_mp_signature(sig, "req-B", b"body")

    assert result is False


def test_verify_mp_signature_extra_fields_in_signature():
    """Extra fields in x_signature are tolerated as long as ts and v1 are present."""
    secret = "secret"
    request_id = "req-007"
    ts = "1700000000"
    manifest = f"id:{request_id};ts:{ts};"
    v1 = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    sig = f"ts={ts},v1={v1},extra=ignoreme"

    with patch("api.routes.webhooks.MP_SECRET_KEY", secret):
        result = _verify_mp_signature(sig, request_id, b"body")

    assert result is True
