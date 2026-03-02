"""Tests for call endpoints: upload, webhook, list, detail, transcript."""

import io
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.call import Call, CallStatus, IntentClassification
from tests.factories import (
    create_call,
    create_tenant,
    create_user,
    create_admin,
)
from tests.fixtures.audio import create_dummy_wav, create_dummy_mp3


class TestUploadCall:
    """POST /api/v1/calls/upload"""

    @patch("app.api.calls.process_call", create=True)
    def test_upload_call_wav(self, mock_task, client: TestClient, auth_headers, dummy_audio_files, tmp_path):
        wav_path = dummy_audio_files["hot_wav"]
        with open(wav_path, "rb") as f:
            resp = client.post(
                "/api/v1/calls/upload",
                files={"file": ("test.wav", f, "audio/wav")},
                data={"language": "en"},
                headers=auth_headers,
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "uploaded"
        assert data["language"] == "en"

    @patch("app.api.calls.process_call", create=True)
    def test_upload_call_mp3(self, mock_task, client: TestClient, auth_headers, dummy_audio_files):
        mp3_path = dummy_audio_files["test_mp3"]
        with open(mp3_path, "rb") as f:
            resp = client.post(
                "/api/v1/calls/upload",
                files={"file": ("test.mp3", f, "audio/mpeg")},
                data={"language": "en"},
                headers=auth_headers,
            )
        assert resp.status_code == 201

    def test_upload_unsupported_format(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/v1/calls/upload",
            files={"file": ("test.txt", io.BytesIO(b"not audio"), "text/plain")},
            data={"language": "en"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]

    @patch("app.config.settings.MAX_FILE_SIZE_MB", 0)
    def test_upload_file_too_large(self, client: TestClient, auth_headers, dummy_audio_files):
        """File exceeds maximum size."""
        wav_path = dummy_audio_files["hot_wav"]
        with open(wav_path, "rb") as f:
            resp = client.post(
                "/api/v1/calls/upload",
                files={"file": ("test.wav", f, "audio/wav")},
                data={"language": "en"},
                headers=auth_headers,
            )
        assert resp.status_code == 413


class TestWebhookCall:
    """POST /api/v1/calls/webhook"""

    @patch("app.api.calls.process_call", create=True)
    def test_webhook_call(self, mock_task, client: TestClient, auth_headers):
        resp = client.post(
            "/api/v1/calls/webhook",
            json={
                "recording_url": "https://example.com/recording.wav",
                "lead_name": "Test Lead",
                "language": "en",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "uploaded"
        assert data["lead_name"] == "Test Lead"


class TestListCalls:
    """GET /api/v1/calls"""

    def test_list_calls_empty(self, client: TestClient, auth_headers):
        resp = client.get("/api/v1/calls", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_calls_with_data(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant, test_admin
    ):
        admin, _ = test_admin
        for i in range(3):
            create_call(db_session, test_tenant, agent=admin)
        db_session.commit()

        resp = client.get("/api/v1/calls", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_list_calls_filter_by_agent(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant, test_admin, test_agent
    ):
        admin, _ = test_admin
        agent, _ = test_agent
        create_call(db_session, test_tenant, agent=admin)
        create_call(db_session, test_tenant, agent=agent)
        db_session.commit()

        resp = client.get(
            f"/api/v1/calls?agent_id={agent.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_list_calls_filter_by_intent(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant, test_admin
    ):
        admin, _ = test_admin
        create_call(db_session, test_tenant, agent=admin,
                     status=CallStatus.completed,
                     intent_classification=IntentClassification.hot, overall_score=80)
        create_call(db_session, test_tenant, agent=admin,
                     status=CallStatus.completed,
                     intent_classification=IntentClassification.cold, overall_score=30)
        db_session.commit()

        resp = client.get(
            "/api/v1/calls?intent_classification=hot",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["intent_classification"] == "hot"

    def test_list_calls_filter_by_date_range(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant, test_admin
    ):
        admin, _ = test_admin
        create_call(db_session, test_tenant, agent=admin)
        db_session.commit()

        resp = client.get(
            "/api/v1/calls?date_from=2020-01-01T00:00:00&date_to=2099-12-31T23:59:59",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1


class TestGetCall:
    """GET /api/v1/calls/{id}"""

    def test_get_call_detail(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant, test_admin
    ):
        admin, _ = test_admin
        call = create_call(db_session, test_tenant, agent=admin, lead_name="Detail Lead")
        db_session.commit()

        resp = client.get(f"/api/v1/calls/{call.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["lead_name"] == "Detail Lead"

    def test_get_call_not_found(self, client: TestClient, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/calls/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_call_other_tenant(
        self, client: TestClient, auth_headers,
        db_session: Session, second_tenant,
    ):
        """Tenant A admin cannot see Tenant B's call."""
        other_call = create_call(db_session, second_tenant)
        db_session.commit()

        resp = client.get(f"/api/v1/calls/{other_call.id}", headers=auth_headers)
        assert resp.status_code == 404


class TestGetTranscript:
    """GET /api/v1/calls/{id}/transcript"""

    def test_get_transcript(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant, test_admin
    ):
        admin, _ = test_admin
        call = create_call(
            db_session, test_tenant, agent=admin,
            status=CallStatus.completed,
            transcript_raw="Hello, this is a test transcript.",
            transcript_segments=[
                {"speaker": "Agent", "start_time": 0.0, "end_time": 5.0, "text": "Hello, this is a test transcript."},
            ],
        )
        db_session.commit()

        resp = client.get(f"/api/v1/calls/{call.id}/transcript", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["segments"]) == 1
        assert data["segments"][0]["speaker"] == "Agent"

    def test_get_transcript_before_processing(
        self, client: TestClient, auth_headers, db_session: Session, test_tenant, test_admin
    ):
        admin, _ = test_admin
        call = create_call(
            db_session, test_tenant, agent=admin,
            status=CallStatus.uploaded,
        )
        db_session.commit()

        resp = client.get(f"/api/v1/calls/{call.id}/transcript", headers=auth_headers)
        assert resp.status_code == 422
