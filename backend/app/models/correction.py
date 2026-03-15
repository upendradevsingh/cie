import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import GUID
from sqlalchemy import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Correction(TimestampMixin, Base):
    __tablename__ = "corrections"

    extraction_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("extractions.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), nullable=False, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), nullable=True
    )

    # What was corrected
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    original_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrected_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    correction_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Correction type: accept|reject|modify
    correction_type: Mapped[str] = mapped_column(
        String(20), default="modify", nullable=False
    )

    # Attributes delta (for JSONB field corrections)
    attributes_delta: Mapped[Optional[dict]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Relationships
    extraction: Mapped["Extraction"] = relationship(
        "Extraction", back_populates="corrections"
    )
