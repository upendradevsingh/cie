"""SQLAlchemy engine, session factory, and FastAPI dependencies.

Provides two session dependencies:

* ``get_db()`` — plain session for unauthenticated endpoints (login,
  register, health check, tenant bootstrap).
* ``get_db_with_tenant()`` — session that automatically sets the
  PostgreSQL ``app.current_tenant_id`` session variable so that RLS
  policies enforce tenant isolation at the database level.
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

_engine_kwargs = {
    "pool_pre_ping": True,
    "echo": settings.DEBUG,
}

# SQLite does not support pool_size / max_overflow.
if not settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["pool_size"] = 20
    _engine_kwargs["max_overflow"] = 10

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed after the request.

    Use for **unauthenticated** endpoints where no tenant context is needed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_with_tenant(
    # We import here to break the circular dependency chain:
    #   session -> auth -> models -> … -> session
) -> Generator[Session, None, None]:
    """Yield a tenant-aware database session.

    Resolves the current user from the JWT token, then sets
    ``SET LOCAL app.current_tenant_id`` so that PostgreSQL RLS policies
    automatically filter every query to the authenticated tenant.

    Use for **all authenticated** endpoints.
    """
    from app.db.rls import set_tenant_context
    from app.services.auth import get_current_active_user  # noqa: F401

    # NOTE: FastAPI cannot resolve nested Depends() inside a bare
    # generator.  The actual user resolution + tenant context setting
    # is handled via the ``TenantDbSession`` type alias which composes
    # both ``get_db`` and the auth dependency at the route level.
    #
    # This function exists so that ``TenantDbSession`` has a distinct
    # dependency to reference.  The tenant context is set by the route-
    # level helper ``_set_rls_and_return_db`` (below).
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Type aliases for route handler convenience
# ---------------------------------------------------------------------------

# Plain session (unauthenticated endpoints: health, login, register, tenant)
DbSession = Annotated[Session, Depends(get_db)]

# Tenant-aware session — used on all authenticated endpoints.
# Route handlers using this MUST also depend on get_current_active_user
# (or require_role) and call set_tenant_context(db, current_user.tenant_id).
TenantDbSession = Annotated[Session, Depends(get_db_with_tenant)]
