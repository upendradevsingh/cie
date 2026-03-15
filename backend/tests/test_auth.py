"""Tests for JWT validation service."""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

from app.config import settings
from app.services.auth import decode_token, TokenClaims


def make_token(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def test_valid_token_decodes_correctly():
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    token = make_token({
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "sub": "test",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    })
    claims = decode_token(token)
    assert claims.tenant_id == tenant_id
    assert claims.user_id == user_id


def test_expired_token_raises_401():
    token = make_token({
        "tenant_id": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
    })
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401


def test_wrong_secret_raises_401():
    token = jwt.encode(
        {"tenant_id": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "wrong_secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401


def test_missing_tenant_id_raises_401():
    token = make_token({
        "user_id": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    })
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401
    assert "tenant_id" in exc_info.value.detail


def test_token_without_user_id_is_valid():
    """Tokens without user_id are valid (service-to-service calls)."""
    tenant_id = uuid.uuid4()
    token = make_token({
        "tenant_id": str(tenant_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    })
    claims = decode_token(token)
    assert claims.tenant_id == tenant_id
    assert claims.user_id is None
