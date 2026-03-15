"""Test configuration and fixtures for CIE."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.models.base import Base
from app.main import app
from app.db.session import get_db_with_tenant, get_db

# Use SQLite for tests
TEST_DATABASE_URL = "sqlite:///./test_cie.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

TEST_TENANT_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
TEST_USER_ID = uuid.UUID("87654321-4321-8765-4321-876543218765")


def make_test_token(tenant_id: uuid.UUID = TEST_TENANT_ID, user_id: uuid.UUID = TEST_USER_ID) -> str:
    payload = {
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "sub": "test_user",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db(db_engine) -> Generator[Session, None, None]:
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield db

    app.dependency_overrides[get_db_with_tenant] = override_get_db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict:
    token = make_test_token()
    return {"Authorization": f"Bearer {token}"}
