"""Quality parameter configuration and per-call quality scores."""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class QualityParameter(TimestampMixin, Base):
    """Tenant-configurable scoring parameter (e.g. "Objection Handling")."""

    __tablename__ = "quality_parameters"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    category: Mapped[str | None] = mapped_column(String(127), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Relationships ────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="quality_parameters")  # noqa: F821
    call_scores: Mapped[list["CallQualityScore"]] = relationship(
        "CallQualityScore", back_populates="parameter", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_qp_tenant_active", "tenant_id", "is_active"),
        Index("ix_qp_tenant_category", "tenant_id", "category"),
    )

    def __repr__(self) -> str:
        return f"<QualityParameter {self.name!r} weight={self.weight}>"


class CallQualityScore(TimestampMixin, Base):
    """Score awarded to a single call for one quality parameter."""

    __tablename__ = "call_quality_scores"

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parameter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quality_parameters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    call: Mapped["Call"] = relationship("Call", back_populates="quality_scores")  # noqa: F821
    parameter: Mapped["QualityParameter"] = relationship(
        "QualityParameter", back_populates="call_scores"
    )

    __table_args__ = (
        Index("ix_cqs_call_param", "call_id", "parameter_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<CallQualityScore call={self.call_id} param={self.parameter_id} score={self.score}>"
