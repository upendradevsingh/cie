"""Tests for outbound webhook delivery."""

import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.integration import Integration
from app.services.analysis.llm_analyzer import (
    AnalysisResult,
    QualityScore,
    IntentSignalResult,
    ActionItem as AnalysisActionItem,
    PersonaResult,
)
from app.tasks.call_processing import _push_to_integrations, _send_webhook
from tests.factories import create_call, create_integration, create_tenant, create_admin
from app.models.call import CallStatus, IntentClassification


def _make_analysis_result():
    """Create a minimal AnalysisResult for testing."""
    return AnalysisResult(
        quality_scores=[
            QualityScore("Test Param", 8.0, "Good"),
        ],
        overall_score=80.0,
        lead_intent_score=75.0,
        intent_classification="hot",
        intent_signals=[
            IntentSignalResult("Budget Mentioned", True, "Customer mentioned 5L budget"),
        ],
        persona=PersonaResult(
            type="Ready Buyer",
            budget_score=8.0,
            authority_score=7.0,
            need_score=9.0,
            timeline_score=8.0,
            discovery_insights=["Homeowner in Mumbai"],
        ),
        action_items=[
            AnalysisActionItem("Schedule site visit", "follow_up", "immediate"),
        ],
        path_to_conversion="Follow up with proposal",
        rebuttals=["Price comparison rebuttal"],
        key_data_points={"budget": "5L"},
        follow_up_urgency="immediate",
        call_summary="Good call with hot lead",
    )


class TestWebhookDelivery:
    """Tests for the webhook delivery mechanism."""

    def test_webhook_delivery_success(
        self, db_session: Session, test_tenant, test_admin,
    ):
        admin, _ = test_admin
        integration = create_integration(
            db_session, test_tenant,
            config={"url": "https://crm.example.com/hook"},
        )
        call = create_call(
            db_session, test_tenant, agent=admin,
            status=CallStatus.completed,
            intent_classification=IntentClassification.hot,
            overall_score=80.0,
        )
        db_session.commit()

        analysis = _make_analysis_result()

        with patch("app.tasks.call_processing.httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_client_instance)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client_instance.post.return_value = mock_response

            _push_to_integrations(db_session, call, analysis)

            mock_client_instance.post.assert_called_once()
            call_args = mock_client_instance.post.call_args
            assert "crm.example.com" in call_args[1].get("url", call_args[0][0] if call_args[0] else "")

    def test_webhook_delivery_failure_non_blocking(
        self, db_session: Session, test_tenant, test_admin,
    ):
        """HTTP error doesn't fail the task — just logs a warning."""
        admin, _ = test_admin
        integration = create_integration(
            db_session, test_tenant,
            config={"url": "https://crm.example.com/hook"},
        )
        call = create_call(
            db_session, test_tenant, agent=admin,
            status=CallStatus.completed,
            intent_classification=IntentClassification.hot,
            overall_score=80.0,
        )
        db_session.commit()

        analysis = _make_analysis_result()

        with patch("app.tasks.call_processing.httpx.Client") as MockClient:
            mock_client_instance = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_client_instance)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            import httpx
            mock_client_instance.post.side_effect = httpx.HTTPError("Connection refused")

            # Should NOT raise — just log warning
            _push_to_integrations(db_session, call, analysis)

    def test_webhook_no_url_configured(
        self, db_session: Session, test_tenant, test_admin,
    ):
        """Integration with no URL skips gracefully."""
        admin, _ = test_admin
        integration = create_integration(
            db_session, test_tenant,
            config={},  # No URL
        )
        call = create_call(
            db_session, test_tenant, agent=admin,
            status=CallStatus.completed,
        )
        db_session.commit()

        analysis = _make_analysis_result()

        # Should not raise any exception
        _push_to_integrations(db_session, call, analysis)
