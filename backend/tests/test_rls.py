"""Test that PostgreSQL Row-Level Security correctly isolates tenants.

These tests require a running PostgreSQL instance with the RLS migration
applied.  They prove that:

1. Queries with tenant A's context only return tenant A's rows.
2. Queries with tenant B's context only return tenant B's rows.
3. Queries **without** any tenant context return NO rows (fail-closed).

Run with::

    pytest backend/tests/test_rls.py -v

Set ``DATABASE_URL`` in your environment to point to the test database.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.rls import clear_tenant_context, set_tenant_context
from app.db.session import SessionLocal
from app.models.call import Call, CallStatus
from app.models.quality import QualityParameter
from app.models.tenant import Tenant
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db() -> Session:
    """Provide a database session for the entire test module."""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def tenant_a(db: Session) -> Tenant:
    """Create a test tenant A."""
    tenant = Tenant(
        name="Tenant A (RLS Test)",
        slug=f"rls-test-a-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture(scope="module")
def tenant_b(db: Session) -> Tenant:
    """Create a test tenant B."""
    tenant = Tenant(
        name="Tenant B (RLS Test)",
        slug=f"rls-test-b-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture(scope="module")
def seed_data(db: Session, tenant_a: Tenant, tenant_b: Tenant) -> dict:
    """Create test rows in both tenants and return their IDs."""
    # Temporarily set tenant context for inserts (RLS is enforced even for the owner).
    # Create users
    set_tenant_context(db, tenant_a.id)
    user_a = User(
        tenant_id=tenant_a.id,
        email=f"agent-a-{uuid.uuid4().hex[:6]}@rls-test.local",
        hashed_password="$2b$12$fakehashfortest",
        full_name="Agent A",
        role=UserRole.agent,
        is_active=True,
    )
    db.add(user_a)
    db.flush()

    call_a = Call(
        tenant_id=tenant_a.id,
        agent_id=user_a.id,
        status=CallStatus.uploaded,
        language="en",
    )
    db.add(call_a)
    db.commit()
    db.refresh(user_a)
    db.refresh(call_a)

    set_tenant_context(db, tenant_b.id)
    user_b = User(
        tenant_id=tenant_b.id,
        email=f"agent-b-{uuid.uuid4().hex[:6]}@rls-test.local",
        hashed_password="$2b$12$fakehashfortest",
        full_name="Agent B",
        role=UserRole.agent,
        is_active=True,
    )
    db.add(user_b)
    db.flush()

    call_b = Call(
        tenant_id=tenant_b.id,
        agent_id=user_b.id,
        status=CallStatus.uploaded,
        language="en",
    )
    db.add(call_b)
    db.commit()
    db.refresh(user_b)
    db.refresh(call_b)

    clear_tenant_context(db)

    return {
        "tenant_a_id": tenant_a.id,
        "tenant_b_id": tenant_b.id,
        "user_a_id": user_a.id,
        "user_b_id": user_b.id,
        "call_a_id": call_a.id,
        "call_b_id": call_b.id,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRLSIsolation:
    """Verify that RLS policies correctly isolate tenant data."""

    def test_tenant_a_sees_only_own_calls(self, db: Session, seed_data: dict) -> None:
        """When context is set to tenant A, only tenant A's calls are visible."""
        set_tenant_context(db, seed_data["tenant_a_id"])

        calls = db.query(Call).all()
        tenant_ids = {c.tenant_id for c in calls}

        assert seed_data["tenant_a_id"] in tenant_ids or len(calls) > 0
        assert seed_data["tenant_b_id"] not in tenant_ids

        clear_tenant_context(db)

    def test_tenant_b_sees_only_own_calls(self, db: Session, seed_data: dict) -> None:
        """When context is set to tenant B, only tenant B's calls are visible."""
        set_tenant_context(db, seed_data["tenant_b_id"])

        calls = db.query(Call).all()
        tenant_ids = {c.tenant_id for c in calls}

        assert seed_data["tenant_b_id"] in tenant_ids or len(calls) > 0
        assert seed_data["tenant_a_id"] not in tenant_ids

        clear_tenant_context(db)

    def test_tenant_a_sees_only_own_users(self, db: Session, seed_data: dict) -> None:
        """User queries are also RLS-protected."""
        set_tenant_context(db, seed_data["tenant_a_id"])

        users = db.query(User).all()
        tenant_ids = {u.tenant_id for u in users}

        assert seed_data["tenant_b_id"] not in tenant_ids

        clear_tenant_context(db)

    def test_no_context_returns_nothing(self, db: Session, seed_data: dict) -> None:
        """Without setting app.current_tenant_id, RLS returns NO rows (fail-closed).

        This is the most critical test — it ensures that a missing tenant
        context does not accidentally expose all data.
        """
        # Reset any previous context
        clear_tenant_context(db)

        calls = db.query(Call).all()
        users = db.query(User).all()

        # Fail-closed: no rows should be visible
        assert len(calls) == 0, (
            f"Expected 0 calls without tenant context, got {len(calls)}"
        )
        assert len(users) == 0, (
            f"Expected 0 users without tenant context, got {len(users)}"
        )

    def test_cross_tenant_call_not_found(self, db: Session, seed_data: dict) -> None:
        """Querying for a specific call from another tenant returns None."""
        set_tenant_context(db, seed_data["tenant_a_id"])

        # Try to load tenant B's call while in tenant A's context
        cross_call = (
            db.query(Call).filter(Call.id == seed_data["call_b_id"]).first()
        )
        assert cross_call is None, (
            "Tenant A should not be able to see Tenant B's call"
        )

        clear_tenant_context(db)

    def test_cross_tenant_user_not_found(self, db: Session, seed_data: dict) -> None:
        """Querying for a specific user from another tenant returns None."""
        set_tenant_context(db, seed_data["tenant_b_id"])

        # Try to load tenant A's user while in tenant B's context
        cross_user = (
            db.query(User).filter(User.id == seed_data["user_a_id"]).first()
        )
        assert cross_user is None, (
            "Tenant B should not be able to see Tenant A's user"
        )

        clear_tenant_context(db)
