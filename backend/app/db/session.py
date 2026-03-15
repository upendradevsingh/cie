"""Database session management for CIE."""
import logging
import uuid
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

IS_POSTGRES = settings.DATABASE_URL.startswith("postgresql")

_engine_kwargs: dict = {
    "pool_pre_ping": True,
    "echo": settings.DEBUG,
}

if IS_POSTGRES:
    _engine_kwargs["pool_size"] = 20
    _engine_kwargs["max_overflow"] = 10

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: plain database session (for health check)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_tenant_context(db: Session, tenant_id: uuid.UUID) -> None:
    """Set PostgreSQL RLS tenant context for this transaction."""
    if IS_POSTGRES:
        try:
            db.execute(
                text("SET LOCAL app.current_tenant_id = :tid"),
                {"tid": str(tenant_id)},
            )
        except Exception as e:
            logger.warning("Failed to set tenant context: %s", e)


def get_db_with_tenant() -> Generator[Session, None, None]:
    """FastAPI dependency: database session (tenant context set by route handler)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
