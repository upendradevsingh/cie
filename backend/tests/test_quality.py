"""Tests for quality parameter CRUD and QA override."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.call import CallStatus, IntentClassification
from tests.factories import (
    create_call,
    create_quality_parameter,
    create_call_quality_score,
)


class TestQualityParameterCRUD:
    """CRUD operations on quality parameters."""

    def test_create_quality_parameter(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/v1/quality-parameters",
            json={
                "name": "Rapport Building",
                "description": "Building rapport with the customer",
                "weight": 0.8,
                "category": "Communication",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Rapport Building"
        assert data["weight"] == 0.8
        assert data["is_active"] is True

    def test_list_quality_parameters(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant
    ):
        create_quality_parameter(db_session, test_tenant, name="Param A")
        create_quality_parameter(db_session, test_tenant, name="Param B")
        db_session.commit()

        resp = client.get("/api/v1/quality-parameters", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    def test_update_quality_parameter(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant
    ):
        param = create_quality_parameter(db_session, test_tenant, name="Old Name")
        db_session.commit()

        resp = client.put(
            f"/api/v1/quality-parameters/{param.id}",
            json={"name": "New Name", "weight": 0.5},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Name"
        assert data["weight"] == 0.5

    def test_delete_quality_parameter(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant
    ):
        param = create_quality_parameter(db_session, test_tenant, name="To Delete")
        db_session.commit()

        resp = client.delete(
            f"/api/v1/quality-parameters/{param.id}",
            headers=auth_headers,
        )
        assert resp.status_code in (200, 204)


class TestQAOverride:
    """PUT /api/v1/calls/{id}/qa-override"""

    def test_qa_override_scores(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant, test_admin
    ):
        admin, _ = test_admin
        param = create_quality_parameter(db_session, test_tenant, name="Test Param", weight=1.0)
        call = create_call(
            db_session, test_tenant, agent=admin,
            status=CallStatus.completed,
            overall_score=50.0,
        )
        create_call_quality_score(db_session, call, param, score=5.0)
        db_session.commit()

        resp = client.put(
            f"/api/v1/calls/{call.id}/qa-override",
            json={
                "scores": [{
                    "parameter_id": str(param.id),
                    "new_score": 9.0,
                    "justification": "Agent was actually excellent",
                }],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Score should have been recalculated
        assert data["overall_score"] is not None

    def test_qa_override_requires_admin_role(
        self, client: TestClient, test_agent, db_session: Session, test_tenant
    ):
        """Agent role cannot override scores."""
        agent, agent_headers = test_agent
        param = create_quality_parameter(db_session, test_tenant, name="Param")
        call = create_call(
            db_session, test_tenant, agent=agent,
            status=CallStatus.completed, overall_score=50.0,
        )
        db_session.commit()

        resp = client.put(
            f"/api/v1/calls/{call.id}/qa-override",
            json={
                "scores": [{
                    "parameter_id": str(param.id),
                    "new_score": 9.0,
                    "justification": "Override attempt",
                }],
            },
            headers=agent_headers,
        )
        assert resp.status_code == 403

    def test_qa_override_nonexistent_call(self, client: TestClient, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = client.put(
            f"/api/v1/calls/{fake_id}/qa-override",
            json={
                "scores": [{
                    "parameter_id": str(uuid.uuid4()),
                    "new_score": 5.0,
                    "justification": "Test",
                }],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404
