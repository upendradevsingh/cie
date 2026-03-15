"""Tests for the conversations API endpoints."""
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_submit_conversation_requires_auth(client):
    response = client.post("/api/v1/conversations", json={
        "source": "text",
        "profile": "performance",
        "segments": [{"speaker": "user1", "text": "Hello"}],
    })
    assert response.status_code == 403  # No auth header


def test_submit_conversation_with_segments(client, auth_headers):
    with patch("app.api.conversations.process_conversation") as mock_task:
        mock_task.delay = lambda *args, **kwargs: None
        response = client.post(
            "/api/v1/conversations",
            json={
                "source": "text",
                "profile": "performance",
                "participants": [{"externalId": "u1", "name": "Alice", "role": "manager"}],
                "segments": [
                    {"speaker": "u1", "text": "I will finish the report by Friday."}
                ],
            },
            headers=auth_headers,
        )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert data["profile_id"] == "performance"
    assert data["source"] == "text"
    assert "id" in data


def test_submit_conversation_invalid_profile(client, auth_headers):
    response = client.post(
        "/api/v1/conversations",
        json={
            "source": "text",
            "profile": "nonexistent_profile_xyz",
            "segments": [{"speaker": "u1", "text": "Hello"}],
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "nonexistent_profile_xyz" in response.json()["detail"]


def test_get_conversation_not_found(client, auth_headers):
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/conversations/{fake_id}", headers=auth_headers)
    assert response.status_code == 404


def test_get_conversation(client, auth_headers):
    # First create one
    with patch("app.api.conversations.process_conversation") as mock_task:
        mock_task.delay = lambda *args, **kwargs: None
        create_resp = client.post(
            "/api/v1/conversations",
            json={
                "source": "chat",
                "profile": "sales",
                "segments": [{"speaker": "agent", "text": "Hi, how can I help?"}],
            },
            headers=auth_headers,
        )
    assert create_resp.status_code == 202
    conversation_id = create_resp.json()["id"]

    # Then get it
    get_resp = client.get(f"/api/v1/conversations/{conversation_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == conversation_id


def test_list_conversations(client, auth_headers):
    response = client.get("/api/v1/conversations", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
