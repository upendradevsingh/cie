"""DataCaptureQuestion model — tenant-configurable questions for LLM extraction."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DataCaptureQuestion(TimestampMixin, Base):
    __tablename__ = "data_capture_questions"

    # ── Ownership ────────────────────────────────────────────────────────
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Question configuration ───────────────────────────────────────────
    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="The question to ask the LLM (e.g., 'Does the customer have a quote from a competitor?')",
    )
    field_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Key name for the extracted data (e.g., 'has_competitor_quote')",
    )
    expected_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="text",
        doc="Expected answer type: 'text', 'boolean', 'number', 'list'",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Additional context or instructions for the LLM",
    )

    # ── Display & Ordering ───────────────────────────────────────────────
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Order in which to display/process questions",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # ── Category ─────────────────────────────────────────────────────────
    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Optional category (e.g., 'competitive', 'budget', 'timeline')",
    )

    # ── Relationships ────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant")  # noqa: F821

    __table_args__ = (
        Index("ix_data_capture_questions_tenant_active", "tenant_id", "is_active"),
        Index("ix_data_capture_questions_display_order", "display_order"),
    )

    def __repr__(self) -> str:
        return f"<DataCaptureQuestion {self.field_name}: {self.question[:50]}...>"
