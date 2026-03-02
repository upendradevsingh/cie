"""Test tenant data isolation.

When running on SQLite (unit tests), these verify that API endpoints
correctly filter by tenant_id.  On PostgreSQL, the actual RLS policies
provide an additional layer of enforcement tested in integration tests.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.call import Call, CallStatus, IntentClassification
from app.models.user import UserRole
from app.services.auth import create_access_token
from tests.factories import create_call, create_tenant, create_user, create_admin


class TestTenantIsolation:
    """Verify that tenant A cannot see tenant B's data through the API."""

    def test_tenant_a_cannot_see_tenant_b_calls(
        self, client: TestClient, db_session: Session, test_tenant, second_tenant,
    ):
        """Calls created under tenant B are invisible to tenant A."""
        admin_a = create_admin(
            db_session, test_tenant,
            email="admin-a@test.com", full_name="Admin A", password="pass123",
        )
        admin_b = create_admin(
            db_session, second_tenant,
            email="admin-b@test.com", full_name="Admin B", password="pass123",
        )
        db_session.commit()

        # Create a call in each tenant
        call_a = create_call(
            db_session, test_tenant, agent=admin_a,
            status=CallStatus.completed, overall_score=80.0,
        )
        call_b = create_call(
            db_session, second_tenant, agent=admin_b,
            status=CallStatus.completed, overall_score=60.0,
        )
        db_session.commit()

        # Authenticate as admin A
        token_a = create_access_token(data={
            "sub": str(admin_a.id),
            "tenant_id": str(test_tenant.id),
            "role": "admin",
        })
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # List calls — should only see tenant A's call
        resp = client.get("/api/v1/calls", headers=headers_a)
        assert resp.status_code == 200
        data = resp.json()
        call_ids = [c["id"] for c in data["items"]]
        assert str(call_a.id) in call_ids
        assert str(call_b.id) not in call_ids

    def test_tenant_b_cannot_see_tenant_a_call_detail(
        self, client: TestClient, db_session: Session, test_tenant, second_tenant,
    ):
        """Getting a call detail from another tenant returns 404."""
        admin_a = create_admin(
            db_session, test_tenant,
            email="admin-a2@test.com", full_name="Admin A2", password="pass123",
        )
        admin_b = create_admin(
            db_session, second_tenant,
            email="admin-b2@test.com", full_name="Admin B2", password="pass123",
        )
        db_session.commit()

        call_a = create_call(
            db_session, test_tenant, agent=admin_a,
            status=CallStatus.completed,
        )
        db_session.commit()

        # Authenticate as admin B
        token_b = create_access_token(data={
            "sub": str(admin_b.id),
            "tenant_id": str(second_tenant.id),
            "role": "admin",
        })
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Try to access tenant A's call
        resp = client.get(f"/api/v1/calls/{call_a.id}", headers=headers_b)
        assert resp.status_code == 404

    def test_tenant_analytics_only_shows_own_data(
        self, client: TestClient, db_session: Session, test_tenant, second_tenant,
    ):
        """Team analytics only reflects the authenticated tenant's calls."""
        admin_a = create_admin(
            db_session, test_tenant,
            email="admin-a3@test.com", full_name="Admin A3", password="pass123",
        )
        admin_b = create_admin(
            db_session, second_tenant,
            email="admin-b3@test.com", full_name="Admin B3", password="pass123",
        )
        db_session.commit()

        # Create 2 calls for tenant A, 5 calls for tenant B
        for _ in range(2):
            create_call(
                db_session, test_tenant, agent=admin_a,
                status=CallStatus.completed, overall_score=70.0,
            )
        for _ in range(5):
            create_call(
                db_session, second_tenant, agent=admin_b,
                status=CallStatus.completed, overall_score=50.0,
            )
        db_session.commit()

        # Check tenant A's analytics
        token_a = create_access_token(data={
            "sub": str(admin_a.id),
            "tenant_id": str(test_tenant.id),
            "role": "admin",
        })
        headers_a = {"Authorization": f"Bearer {token_a}"}

        resp = client.get("/api/v1/analytics/team", headers=headers_a)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_calls"] == 2  # not 7

    def test_agent_from_other_tenant_not_found(
        self, client: TestClient, db_session: Session, test_tenant, second_tenant,
    ):
        """Looking up an agent from another tenant returns 404."""
        admin_a = create_admin(
            db_session, test_tenant,
            email="admin-a4@test.com", full_name="Admin A4", password="pass123",
        )
        agent_b = create_user(
            db_session, second_tenant,
            email="agent-b4@test.com", full_name="Agent B4",
            role=UserRole.agent,
        )
        db_session.commit()

        token_a = create_access_token(data={
            "sub": str(admin_a.id),
            "tenant_id": str(test_tenant.id),
            "role": "admin",
        })
        headers_a = {"Authorization": f"Bearer {token_a}"}

        resp = client.get(
            f"/api/v1/analytics/agent/{agent_b.id}",
            headers=headers_a,
        )
        assert resp.status_code == 404
