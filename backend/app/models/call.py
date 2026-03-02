"""Call model — the central entity representing a recorded sales call."""

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class CallStatus(str, enum.Enum):
    """Processing lifecycle of a call."""

    uploaded = "uploaded"
    transcribing = "transcribing"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class IntentClassification(str, enum.Enum):
    """Buying-intent bucket assigned after LLM analysis."""

    hot = "hot"
    warm = "warm"
    cold = "cold"


class Call(TimestampMixin, Base):
    __tablename__ = "calls"

    # ── Ownership ────────────────────────────────────────────────────────
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Recording ────────────────────────────────────────────────────────
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Processing status ────────────────────────────────────────────────
    status: Mapped[CallStatus] = mapped_column(
        Enum(CallStatus, name="call_status", create_constraint=True),
        default=CallStatus.uploaded,
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Transcript ───────────────────────────────────────────────────────
    transcript_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_segments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True, default="en")

    # ── Analysis results ─────────────────────────────────────────────────
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    lead_intent_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    intent_classification: Mapped[IntentClassification | None] = mapped_column(
        Enum(IntentClassification, name="intent_classification", create_constraint=True),
        nullable=True,
    )

    # ── Enhanced analysis fields ─────────────────────────────────────────
    escalation_keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    sentiment_keywords: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    call_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    sales_audit_keywords: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Lead / CRM metadata ─────────────────────────────────────────────
    lead_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    lead_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lead_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(127), nullable=True)
    custom_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="calls")  # noqa: F821
    agent: Mapped["User | None"] = relationship("User", back_populates="calls")  # noqa: F821

    quality_scores: Mapped[list["CallQualityScore"]] = relationship(  # noqa: F821
        "CallQualityScore", back_populates="call", cascade="all, delete-orphan"
    )
    intent_signals: Mapped[list["CallIntentSignal"]] = relationship(  # noqa: F821
        "CallIntentSignal", back_populates="call", cascade="all, delete-orphan"
    )
    persona: Mapped["CallPersona | None"] = relationship(  # noqa: F821
        "CallPersona", back_populates="call", uselist=False, cascade="all, delete-orphan"
    )
    action_items: Mapped[list["ActionItem"]] = relationship(  # noqa: F821
        "ActionItem", back_populates="call", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_calls_tenant_status", "tenant_id", "status"),
        Index("ix_calls_tenant_agent", "tenant_id", "agent_id"),
        Index("ix_calls_tenant_created", "tenant_id", "created_at"),
        Index("ix_calls_overall_score", "overall_score"),
        Index("ix_calls_intent_classification", "intent_classification"),
    )

    def __repr__(self) -> str:
        return f"<Call {self.id} status={self.status.value}>"
