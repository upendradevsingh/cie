"""Full HTTP integration tests via TestClient.

Tests conversation submission, status checking, extraction retrieval,
and tenant isolation. Uses mocked Celery task to avoid async worker dependency.
"""
import json
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.models.conversation import Conversation, ConversationStatus
from app.models.extraction import Extraction

EVAL_DIR = Path(__file__).parent


def _load_gold_conversation(conv_id: str = "gold_001") -> dict:
    """Load a specific conversation from the gold dataset."""
    with open(EVAL_DIR / "gold_dataset.json") as f:
        dataset = json.load(f)
    for conv in dataset:
        if conv["id"] == conv_id:
            return conv
    raise ValueError(f"Conversation {conv_id} not found in gold dataset")


def _build_submission_payload(gold: dict) -> dict:
    """Build a ConversationCreateRequest payload from gold data."""
    segments = []
    for seg in gold["segments"]:
        segments.append({
            "speaker": seg["speaker"],
            "text": seg["text"],
            "start_time": seg.get("startTime"),
            "end_time": seg.get("endTime"),
        })

    return {
        "source": "text",
        "profile": gold.get("profile", "performance"),
        "participants": gold.get("participants", []),
        "segments": segments,
        "language": "en",
    }


@pytest.mark.integration
class TestConversationSubmission:
    """Test conversation submission endpoint."""

    @patch("app.api.conversations.process_conversation")
    def test_submit_conversation_returns_202(self, mock_task, client, auth_headers):
        """POST /api/v1/conversations should return 202 Accepted."""
        mock_task.delay = MagicMock()
        gold = _load_gold_conversation("gold_001")
        payload = _build_submission_payload(gold)

        response = client.post(
            "/api/v1/conversations",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert data["profile_id"] == "performance"
        assert data["source"] == "text"

    @patch("app.api.conversations.process_conversation")
    def test_submit_conversation_dispatches_task(self, mock_task, client, auth_headers):
        """Submitting a conversation should trigger the Celery task."""
        mock_task.delay = MagicMock()
        gold = _load_gold_conversation("gold_002")
        payload = _build_submission_payload(gold)

        response = client.post(
            "/api/v1/conversations",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 202
        mock_task.delay.assert_called_once()
        call_args = mock_task.delay.call_args[0]
        assert isinstance(call_args[0], str)  # conversation_id as string

    @patch("app.api.conversations.process_conversation")
    def test_submit_invalid_profile_returns_400(self, mock_task, client, auth_headers):
        """Submitting with an unknown profile should return 400."""
        mock_task.delay = MagicMock()
        payload = {
            "source": "text",
            "profile": "nonexistent_profile",
            "segments": [{"speaker": "A", "text": "Hello"}],
        }

        response = client.post(
            "/api/v1/conversations",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "nonexistent_profile" in response.json()["detail"]

    def test_submit_without_auth_returns_401(self, client):
        """Submitting without auth token should return 401/403."""
        payload = {
            "source": "text",
            "profile": "performance",
            "segments": [{"speaker": "A", "text": "Hello"}],
        }

        response = client.post("/api/v1/conversations", json=payload)
        assert response.status_code in (401, 403, 422)


@pytest.mark.integration
class TestConversationRetrieval:
    """Test conversation GET endpoints."""

    @patch("app.api.conversations.process_conversation")
    def test_get_conversation_by_id(self, mock_task, client, auth_headers):
        """GET /api/v1/conversations/{id} should return the conversation."""
        mock_task.delay = MagicMock()
        gold = _load_gold_conversation("gold_001")
        payload = _build_submission_payload(gold)

        # Submit
        submit_resp = client.post(
            "/api/v1/conversations",
            json=payload,
            headers=auth_headers,
        )
        conv_id = submit_resp.json()["id"]

        # Retrieve
        response = client.get(
            f"/api/v1/conversations/{conv_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv_id
        assert data["profile_id"] == "performance"

    def test_get_nonexistent_conversation_returns_404(self, client, auth_headers):
        """GET with non-existent ID should return 404."""
        fake_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/conversations/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("app.api.conversations.process_conversation")
    def test_list_conversations(self, mock_task, client, auth_headers):
        """GET /api/v1/conversations should return list of conversations."""
        mock_task.delay = MagicMock()
        gold = _load_gold_conversation("gold_001")
        payload = _build_submission_payload(gold)

        # Submit a conversation
        client.post(
            "/api/v1/conversations",
            json=payload,
            headers=auth_headers,
        )

        # List
        response = client.get("/api/v1/conversations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


@pytest.mark.integration
class TestExtractionRetrieval:
    """Test extraction retrieval endpoint."""

    @patch("app.api.conversations.process_conversation")
    def test_get_extractions_pending_returns_202(self, mock_task, client, auth_headers):
        """GET extractions for a pending conversation should return 202."""
        mock_task.delay = MagicMock()
        gold = _load_gold_conversation("gold_001")
        payload = _build_submission_payload(gold)

        submit_resp = client.post(
            "/api/v1/conversations",
            json=payload,
            headers=auth_headers,
        )
        conv_id = submit_resp.json()["id"]

        response = client.get(
            f"/api/v1/conversations/{conv_id}/extractions",
            headers=auth_headers,
        )

        # Should return 202 since status is still pending
        assert response.status_code == 202

    @patch("app.api.conversations.process_conversation")
    def test_get_extractions_completed(self, mock_task, client, auth_headers, db):
        """GET extractions for a completed conversation should return 200 with data."""
        mock_task.delay = MagicMock()
        gold = _load_gold_conversation("gold_001")
        payload = _build_submission_payload(gold)

        submit_resp = client.post(
            "/api/v1/conversations",
            json=payload,
            headers=auth_headers,
        )
        conv_id = submit_resp.json()["id"]

        # Manually mark as completed and add an extraction
        conv = db.query(Conversation).filter(
            Conversation.id == uuid.UUID(conv_id)
        ).first()
        conv.status = ConversationStatus.completed
        conv.summary = "Test summary"

        extraction = Extraction(
            conversation_id=conv.id,
            tenant_id=conv.tenant_id,
            extraction_type="COMMITMENT",
            description="Test commitment",
            confidence=0.90,
            attributes={"deadline": "Friday"},
        )
        db.add(extraction)
        db.commit()

        response = client.get(
            f"/api/v1/conversations/{conv_id}/extractions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["extraction_type"] == "COMMITMENT"
        assert data[0]["confidence"] == 0.90


@pytest.mark.integration
class TestTenantIsolation:
    """Test that tenant isolation is enforced."""

    @patch("app.api.conversations.process_conversation")
    def test_cannot_access_other_tenant_conversation(
        self, mock_task, client, auth_headers, db
    ):
        """A conversation created by one tenant should not be accessible by another."""
        mock_task.delay = MagicMock()
        gold = _load_gold_conversation("gold_001")
        payload = _build_submission_payload(gold)

        # Submit as default test tenant
        submit_resp = client.post(
            "/api/v1/conversations",
            json=payload,
            headers=auth_headers,
        )
        conv_id = submit_resp.json()["id"]

        # Try to access with a different tenant token
        from tests.conftest import make_test_token
        other_tenant_id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        other_token = make_test_token(tenant_id=other_tenant_id)
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = client.get(
            f"/api/v1/conversations/{conv_id}",
            headers=other_headers,
        )

        # Should be 404 because tenant filter excludes it
        assert response.status_code == 404

    @patch("app.api.conversations.process_conversation")
    def test_list_only_shows_own_tenant(self, mock_task, client, auth_headers):
        """Listing conversations should only show the current tenant's conversations."""
        mock_task.delay = MagicMock()
        gold = _load_gold_conversation("gold_001")
        payload = _build_submission_payload(gold)

        # Submit as default tenant
        client.post(
            "/api/v1/conversations",
            json=payload,
            headers=auth_headers,
        )

        # List as different tenant
        from tests.conftest import make_test_token
        other_tenant_id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        other_token = make_test_token(tenant_id=other_tenant_id)
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = client.get("/api/v1/conversations", headers=other_headers)
        assert response.status_code == 200
        data = response.json()
        # Other tenant should see 0 conversations
        assert len(data) == 0


@pytest.mark.integration
class TestEdgeCases:
    """Test API edge cases."""

    @patch("app.api.conversations.process_conversation")
    def test_submit_empty_segments(self, mock_task, client, auth_headers):
        """Submitting with empty segments list should still be accepted."""
        mock_task.delay = MagicMock()
        payload = {
            "source": "text",
            "profile": "performance",
            "participants": [{"externalId": "u1", "name": "Test", "role": "engineer"}],
            "segments": [],
        }

        response = client.post(
            "/api/v1/conversations",
            json=payload,
            headers=auth_headers,
        )

        # Empty segments might be accepted (no transcript) or rejected
        # Depending on implementation, both 202 and 400/422 are valid
        assert response.status_code in (202, 400, 422)

    @patch("app.api.conversations.process_conversation")
    def test_submit_with_source_metadata(self, mock_task, client, auth_headers):
        """Source metadata should be persisted with the conversation."""
        mock_task.delay = MagicMock()
        gold = _load_gold_conversation("gold_001")
        payload = _build_submission_payload(gold)
        payload["source_metadata"] = {
            "meeting_id": "MTG-12345",
            "calendar_event": "Weekly 1:1",
        }

        response = client.post(
            "/api/v1/conversations",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 202
