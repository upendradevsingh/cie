"""PromptTemplate model — stores tenant-configurable LLM prompt templates."""

import uuid

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PromptTemplate(TimestampMixin, Base):
    __tablename__ = "prompt_templates"

    # ── Ownership ────────────────────────────────────────────────────────
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Template fields ──────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Template identifier (e.g. 'call_analysis')",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    template_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Full Jinja2/text prompt template",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # ── Relationships ────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant")  # noqa: F821

    __table_args__ = (
        Index("ix_prompt_templates_tenant_name", "tenant_id", "name"),
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_prompt_templates_tenant_name_active",
        ),
    )

    def __repr__(self) -> str:
        return f"<PromptTemplate {self.name} v{self.version} tenant={self.tenant_id}>"
