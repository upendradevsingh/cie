import uuid
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Enum as PgEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ConversationStatus(str, Enum):
    pending = "pending"
    transcribing = "transcribing"
    extracting = "extracting"
    completed = "completed"
    failed = "failed"


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Source
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # voice|text|chat|meeting|email
    source_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Audio (optional — skip if text input)
    audio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Transcript
    transcript_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcript_segments: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Processing
    profile_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ConversationStatus] = mapped_column(
        PgEnum(ConversationStatus, name="conversationstatus"),
        default=ConversationStatus.pending,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Participants
    participants: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Callback
    callback_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Summary
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    extractions: Mapped[list["Extraction"]] = relationship(
        "Extraction", back_populates="conversation", cascade="all, delete-orphan"
    )
