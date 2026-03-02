"""Tests for authentication endpoints: login, register, tenant setup."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.services.auth import hash_password
from tests.factories import create_admin, create_tenant, create_user


class TestCreateTenant:
    """POST /api/v1/auth/tenant"""

    def test_create_tenant(self, client: TestClient):
        resp = client.post("/api/v1/auth/tenant", json={
            "tenant_name": "Acme Inc",
            "tenant_slug": "acme-inc",
            "admin_email": "boss@acme.com",
            "admin_password": "securepass123",
            "admin_name": "Boss Man",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["tenant"]["slug"] == "acme-inc"
        assert data["user"]["email"] == "boss@acme.com"
        assert data["user"]["role"] == "admin"
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_create_tenant_duplicate_slug(self, client: TestClient, test_tenant):
        resp = client.post("/api/v1/auth/tenant", json={
            "tenant_name": "Duplicate Corp",
            "tenant_slug": "test-corp",  # same slug as test_tenant
            "admin_email": "new@dup.com",
            "admin_password": "securepass123",
            "admin_name": "New Admin",
        })
        assert resp.status_code == 409


class TestLogin:
    """POST /api/v1/auth/login"""

    def test_login_success(self, client: TestClient, test_admin):
        user, _ = test_admin
        resp = client.post("/api/v1/auth/login", json={
            "email": "admin@testcorp.com",
            "password": "adminpassword123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, test_admin):
        resp = client.post("/api/v1/auth/login", json={
            "email": "admin@testcorp.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, client: TestClient):
        resp = client.post("/api/v1/auth/login", json={
            "email": "nobody@nowhere.com",
            "password": "somepassword123",
        })
        assert resp.status_code == 401

    def test_deactivated_user_cannot_login(
        self, client: TestClient, db_session: Session, test_tenant
    ):
        user = create_user(
            db_session, test_tenant,
            email="inactive@testcorp.com",
            full_name="Inactive User",
            password="inactivepass123",
            is_active=False,
        )
        db_session.commit()

        resp = client.post("/api/v1/auth/login", json={
            "email": "inactive@testcorp.com",
            "password": "inactivepass123",
        })
        assert resp.status_code == 403


class TestRegister:
    """POST /api/v1/auth/register"""

    def test_register_new_user(self, client: TestClient, test_tenant, test_admin):
        """Register a new agent user."""
        resp = client.post("/api/v1/auth/register", json={
            "email": "newagent@testcorp.com",
            "full_name": "New Agent",
            "role": "agent",
            "password": "newagentpass123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newagent@testcorp.com"
        assert data["role"] == "agent"

    def test_register_duplicate_email(self, client: TestClient, test_admin):
        """Cannot register with an existing email."""
        resp = client.post("/api/v1/auth/register", json={
            "email": "admin@testcorp.com",
            "full_name": "Duplicate",
            "role": "agent",
            "password": "duplicatepass123",
        })
        assert resp.status_code == 409


class TestMe:
    """GET /api/v1/auth/me"""

    def test_get_me(self, client: TestClient, test_admin):
        user, headers = test_admin
        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@testcorp.com"
        assert data["role"] == "admin"

    def test_get_me_unauthenticated(self, client: TestClient):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
