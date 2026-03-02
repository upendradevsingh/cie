"""Shared test fixtures: test DB, FastAPI client, auth, factories.

Uses SQLite in-memory for most tests (fast, no external dependencies).
RLS-specific tests that require PostgreSQL are handled separately.
"""

import os
import uuid
from datetime import datetime
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure test environment variables are set before importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-mock-key")
os.environ.setdefault("DEEPGRAM_API_KEY", "dg-test-mock-key")
os.environ.setdefault("UPLOAD_DIR", "/tmp/saleslens_test_uploads")
os.environ.setdefault("TRANSCRIPTION_PROVIDER", "deepgram")

from app.db.session import get_db, get_db_with_tenant
from app.main import app
from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.services.auth import create_access_token, hash_password
from tests.factories import (
    create_admin,
    create_call,
    create_default_intent_signals,
    create_default_quality_parameters,
    create_integration,
    create_persona_type,
    create_tenant,
    create_user,
)
from tests.fixtures.audio import ensure_dummy_audio_files


# ── SQLite engine for tests ─────────────────────────────────────────────────

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Make SQLite support the SET LOCAL / current_setting calls used by RLS
# by providing no-op functions.
@event.listens_for(TEST_ENGINE, "connect")
def _set_sqlite_pragmas(dbapi_conn, connection_record):
    """Enable WAL mode and create dummy functions for RLS compatibility."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

    # Create no-op function for set_config / current_setting
    dbapi_conn.create_function("set_config", 3, lambda *args: args[1])
    dbapi_conn.create_function("current_setting", 1, lambda *args: "")
    dbapi_conn.create_function("current_setting", 2, lambda *args: "")

    # Provide a date_trunc function that mimics PostgreSQL's date_trunc
    def _date_trunc(unit, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return value
        if unit == "day":
            return value.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif unit == "week":
            # Truncate to Monday of the week
            weekday = value.weekday()
            day = value.replace(hour=0, minute=0, second=0, microsecond=0)
            from datetime import timedelta
            return (day - timedelta(days=weekday)).isoformat()
        elif unit == "month":
            return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    dbapi_conn.create_function("date_trunc", 2, _date_trunc)


TestSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── Core fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _create_tables():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)




@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Yield a DB session that rolls back after each test."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with DB dependency override."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_db_with_tenant] = _override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def test_tenant(db_session: Session) -> Tenant:
    """Create a test tenant and return it."""
    tenant = create_tenant(db_session, name="Test Corp", slug="test-corp")
    db_session.commit()
    return tenant


@pytest.fixture
def second_tenant(db_session: Session) -> Tenant:
    """Create a second tenant for isolation tests."""
    tenant = create_tenant(db_session, name="Other Corp", slug="other-corp")
    db_session.commit()
    return tenant


@pytest.fixture
def test_admin(db_session: Session, test_tenant: Tenant) -> tuple:
    """Create an admin user and return (user, auth_headers)."""
    user = create_admin(
        db_session,
        test_tenant,
        email="admin@testcorp.com",
        full_name="Test Admin",
        password="adminpassword123",
    )
    db_session.commit()

    token = create_access_token(data={
        "sub": str(user.id),
        "tenant_id": str(test_tenant.id),
        "role": "admin",
    })
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


@pytest.fixture
def test_agent(db_session: Session, test_tenant: Tenant) -> tuple:
    """Create an agent user and return (user, auth_headers)."""
    user = create_user(
        db_session,
        test_tenant,
        email="agent@testcorp.com",
        full_name="Test Agent",
        role=UserRole.agent,
        password="agentpassword123",
    )
    db_session.commit()

    token = create_access_token(data={
        "sub": str(user.id),
        "tenant_id": str(test_tenant.id),
        "role": "agent",
    })
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


@pytest.fixture
def auth_headers(test_admin: tuple) -> dict:
    """Return Bearer token headers for the admin user."""
    _, headers = test_admin
    return headers


@pytest.fixture
def dummy_audio_files() -> dict:
    """Ensure dummy audio files exist and return their paths."""
    return ensure_dummy_audio_files()
