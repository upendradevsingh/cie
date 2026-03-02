"""Row-Level Security (RLS) context management.

Provides helper functions to set and clear the PostgreSQL session variable
``app.current_tenant_id`` that RLS policies use to filter rows.  The
variable is set with ``SET LOCAL`` so it is automatically scoped to the
current transaction and does not leak across requests.
"""

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def set_tenant_context(db: Session, tenant_id: UUID) -> None:
    """Set ``app.current_tenant_id`` for the current transaction.

    Uses ``SET LOCAL`` so the value is automatically reset when the
    transaction ends (COMMIT or ROLLBACK).  This is the recommended
    approach for connection-pooled applications.

    Parameters
    ----------
    db:
        An active SQLAlchemy session (must be inside a transaction).
    tenant_id:
        The tenant UUID to bind to this session.
    """
    db.execute(
        text("SET LOCAL app.current_tenant_id = :tid"),
        {"tid": str(tenant_id)},
    )
    logger.debug("RLS tenant context set to %s", tenant_id)


def clear_tenant_context(db: Session) -> None:
    """Reset ``app.current_tenant_id`` to an empty string.

    This is a safety measure — normally ``SET LOCAL`` handles cleanup
    automatically at transaction end.  Call this explicitly if you need
    to switch tenant context within the same transaction (unusual).
    """
    db.execute(text("RESET app.current_tenant_id"))
    logger.debug("RLS tenant context cleared")
