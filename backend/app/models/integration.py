"""CRM integrations and API key management."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Integration(TimestampMixin, Base):
    """Outbound CRM / webhook integration configured per tenant."""

    __tablename__ = "integrations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(127), nullable=False)  # e.g. "webhook", "salesforce"
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="integrations")  # noqa: F821

    __table_args__ = (
        Index("ix_int_tenant_type", "tenant_id", "type"),
        Index("ix_int_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Integration {self.name!r} type={self.type!r}>"


class ApiKey(TimestampMixin, Base):
    """Hashed API key used for inbound webhook authentication."""

    __tablename__ = "api_keys"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_hash: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="api_keys")  # noqa: F821

    __table_args__ = (
        Index("ix_ak_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<ApiKey {self.name!r} active={self.is_active}>"
