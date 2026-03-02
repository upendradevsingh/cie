"""Intent signal configuration and per-call signal detection results."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class IntentSignal(TimestampMixin, Base):
    """Tenant-configurable buying-intent signal (e.g. "Budget mentioned")."""

    __tablename__ = "intent_signals"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="intent_signals")  # noqa: F821
    call_signals: Mapped[list["CallIntentSignal"]] = relationship(
        "CallIntentSignal", back_populates="signal", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_is_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<IntentSignal {self.name!r}>"


class CallIntentSignal(TimestampMixin, Base):
    """Whether a specific intent signal was detected in a call."""

    __tablename__ = "call_intent_signals"

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intent_signals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    call: Mapped["Call"] = relationship("Call", back_populates="intent_signals")  # noqa: F821
    signal: Mapped["IntentSignal"] = relationship(
        "IntentSignal", back_populates="call_signals"
    )

    __table_args__ = (
        Index("ix_cis_call_signal", "call_id", "signal_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<CallIntentSignal call={self.call_id} signal={self.signal_id} detected={self.detected}>"
