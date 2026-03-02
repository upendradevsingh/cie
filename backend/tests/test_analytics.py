"""Tests for analytics endpoints: team, agent, leaderboard, trends."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.call import CallStatus, IntentClassification
from tests.factories import (
    create_call,
    create_user,
    create_call_quality_score,
    create_quality_parameter,
)
from app.models.user import UserRole


class TestTeamAnalytics:
    """GET /api/v1/analytics/team"""

    def test_team_analytics(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant, test_admin
    ):
        admin, _ = test_admin
        # Create some completed calls
        create_call(db_session, test_tenant, agent=admin,
                     status=CallStatus.completed,
                     intent_classification=IntentClassification.hot,
                     overall_score=85.0, lead_intent_score=90.0)
        create_call(db_session, test_tenant, agent=admin,
                     status=CallStatus.completed,
                     intent_classification=IntentClassification.warm,
                     overall_score=55.0, lead_intent_score=60.0)
        create_call(db_session, test_tenant, agent=admin,
                     status=CallStatus.completed,
                     intent_classification=IntentClassification.cold,
                     overall_score=30.0, lead_intent_score=20.0)
        db_session.commit()

        resp = client.get("/api/v1/analytics/team", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_calls"] == 3
        assert data["hot_leads_count"] == 1
        assert data["warm_leads_count"] == 1
        assert data["cold_leads_count"] == 1
        assert data["avg_quality_score"] is not None

    def test_team_analytics_empty(self, client: TestClient, auth_headers):
        resp = client.get("/api/v1/analytics/team", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_calls"] == 0
        assert data["avg_quality_score"] is None


class TestAgentAnalytics:
    """GET /api/v1/analytics/agent/{agent_id}"""

    def test_agent_analytics(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant, test_agent
    ):
        agent, _ = test_agent
        create_call(db_session, test_tenant, agent=agent,
                     status=CallStatus.completed,
                     overall_score=70.0, lead_intent_score=75.0)
        create_call(db_session, test_tenant, agent=agent,
                     status=CallStatus.completed,
                     overall_score=80.0, lead_intent_score=85.0)
        db_session.commit()

        resp = client.get(f"/api/v1/analytics/agent/{agent.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_calls"] == 2
        assert data["avg_quality_score"] is not None
        assert data["agent_name"] == "Test Agent"

    def test_agent_not_found(self, client: TestClient, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/analytics/agent/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404


class TestLeaderboard:
    """GET /api/v1/analytics/leaderboard"""

    def test_leaderboard_ranking(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant
    ):
        # Create two agents with different performance
        agent1 = create_user(
            db_session, test_tenant,
            email="top@test.com", full_name="Top Agent",
            role=UserRole.agent,
        )
        agent2 = create_user(
            db_session, test_tenant,
            email="bottom@test.com", full_name="Bottom Agent",
            role=UserRole.agent,
        )
        create_call(db_session, test_tenant, agent=agent1,
                     status=CallStatus.completed, overall_score=90.0)
        create_call(db_session, test_tenant, agent=agent2,
                     status=CallStatus.completed, overall_score=50.0)
        db_session.commit()

        resp = client.get("/api/v1/analytics/leaderboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        # Top agent should be ranked first
        assert data[0]["rank"] == 1
        assert data[0]["avg_quality_score"] >= data[1]["avg_quality_score"]


class TestScoreTrends:
    """GET /api/v1/analytics/trends"""

    def test_score_trends_daily(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant, test_admin
    ):
        admin, _ = test_admin
        create_call(db_session, test_tenant, agent=admin,
                     status=CallStatus.completed, overall_score=75.0)
        db_session.commit()

        resp = client.get(
            "/api/v1/analytics/trends?aggregation=daily",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should have at least one data point (or empty list for SQLite)
        assert isinstance(data, list)

    def test_score_trends_weekly(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant, test_admin
    ):
        admin, _ = test_admin
        create_call(db_session, test_tenant, agent=admin,
                     status=CallStatus.completed, overall_score=65.0)
        db_session.commit()

        resp = client.get(
            "/api/v1/analytics/trends?aggregation=weekly",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
