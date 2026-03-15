import uuid
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import GUID
from sqlalchemy import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Extraction(TimestampMixin, Base):
    __tablename__ = "extractions"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("conversations.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), nullable=False, index=True
    )

    # Core
    extraction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Attribution
    attributed_to: Mapped[Optional[dict]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Evidence
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_start_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    evidence_end_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Lifecycle
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    # Profile-specific attributes (extensible via JSONB)
    attributes: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False)

    # Correction tracking
    corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    corrected_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="extractions"
    )
    corrections: Mapped[list["Correction"]] = relationship(
        "Correction", back_populates="extraction", cascade="all, delete-orphan"
    )
