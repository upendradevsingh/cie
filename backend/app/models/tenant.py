"""Tenant model — top-level entity for multi-tenant isolation."""

import uuid

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(127), unique=True, nullable=False, index=True)
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ────────────────────────────────────────────────────
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User", back_populates="tenant", cascade="all, delete-orphan"
    )
    calls: Mapped[list["Call"]] = relationship(  # noqa: F821
        "Call", back_populates="tenant", cascade="all, delete-orphan"
    )
    quality_parameters: Mapped[list["QualityParameter"]] = relationship(  # noqa: F821
        "QualityParameter", back_populates="tenant", cascade="all, delete-orphan"
    )
    intent_signals: Mapped[list["IntentSignal"]] = relationship(  # noqa: F821
        "IntentSignal", back_populates="tenant", cascade="all, delete-orphan"
    )
    persona_types: Mapped[list["PersonaType"]] = relationship(  # noqa: F821
        "PersonaType", back_populates="tenant", cascade="all, delete-orphan"
    )
    weekly_reports: Mapped[list["WeeklyReport"]] = relationship(  # noqa: F821
        "WeeklyReport", back_populates="tenant", cascade="all, delete-orphan"
    )
    integrations: Mapped[list["Integration"]] = relationship(  # noqa: F821
        "Integration", back_populates="tenant", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(  # noqa: F821
        "ApiKey", back_populates="tenant", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_tenants_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.slug!r}>"
