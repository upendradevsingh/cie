"""Persona type configuration and per-call BANT persona analysis."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PersonaType(TimestampMixin, Base):
    """Tenant-configurable persona archetype with a BANT profile template."""

    __tablename__ = "persona_types"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    bant_profile: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="persona_types")  # noqa: F821
    call_personas: Mapped[list["CallPersona"]] = relationship(
        "CallPersona", back_populates="persona_type", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_pt_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<PersonaType {self.name!r}>"


class CallPersona(TimestampMixin, Base):
    """BANT analysis and persona classification for a single call."""

    __tablename__ = "call_personas"

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    persona_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persona_types.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── BANT scores (0-10 each) ──────────────────────────────────────────
    budget_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    authority_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    need_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timeline_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Qualitative insights ─────────────────────────────────────────────
    discovery_insights: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    call: Mapped["Call"] = relationship("Call", back_populates="persona")  # noqa: F821
    persona_type: Mapped["PersonaType | None"] = relationship(
        "PersonaType", back_populates="call_personas"
    )

    def __repr__(self) -> str:
        return (
            f"<CallPersona call={self.call_id} "
            f"B={self.budget_score} A={self.authority_score} "
            f"N={self.need_score} T={self.timeline_score}>"
        )
