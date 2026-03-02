"""Lead model — aggregates data from multiple calls per lead."""

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"

    # ── Ownership ────────────────────────────────────────────────────────
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Lead identification ──────────────────────────────────────────────
    lead_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="External lead ID from CRM",
    )
    lead_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lead_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lead_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(127), nullable=True)

    # ── Aggregated scores ────────────────────────────────────────────────
    total_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_intent_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    latest_intent_classification: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "hot", "warm", "cold"

    # ── Progression tracking ─────────────────────────────────────────────
    first_call_date: Mapped[datetime | None] = mapped_column(nullable=True)
    latest_call_date: Mapped[datetime | None] = mapped_column(nullable=True)
    quality_trend: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "improving", "declining", "stable"

    # ── Key insights (aggregated from all calls) ─────────────────────────
    top_objections: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )  # List of most frequent objections
    all_tags: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )  # Unique tags across all calls
    key_pain_points: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )  # Extracted pain points
    competitors_mentioned: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )  # Competitor names
    custom_data: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # Additional custom fields

    # ── BANT aggregate ───────────────────────────────────────────────────
    latest_budget_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    latest_authority_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    latest_need_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    latest_timeline_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    latest_persona_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Next actions ─────────────────────────────────────────────────────
    pending_action_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_action_items: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    follow_up_urgency: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "immediate", "this_week", "next_week", "nurture"
    recommended_next_steps: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )  # AI-generated next steps

    # ── Relationships ────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant")  # noqa: F821
    calls: Mapped[list["Call"]] = relationship(  # noqa: F821
        "Call",
        primaryjoin="and_(foreign(Call.lead_id) == Lead.lead_id, Call.tenant_id == Lead.tenant_id)",
        back_populates=None,
        viewonly=True,
    )

    __table_args__ = (
        Index("ix_leads_tenant_lead_id", "tenant_id", "lead_id", unique=True),
        Index("ix_leads_tenant_classification", "tenant_id", "latest_intent_classification"),
        Index("ix_leads_latest_call_date", "latest_call_date"),
        Index("ix_leads_follow_up_urgency", "follow_up_urgency"),
    )

    def __repr__(self) -> str:
        return f"<Lead {self.lead_id} ({self.lead_name}) calls={self.total_calls}>"
