"""Action items extracted from sales calls."""

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ActionUrgency(str, enum.Enum):
    """Follow-up urgency level."""

    immediate = "immediate"
    this_week = "this_week"
    next_week = "next_week"
    nurture = "nurture"


class ActionItem(TimestampMixin, Base):
    """A concrete next-step or action extracted from a call transcript."""

    __tablename__ = "action_items"

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(127), nullable=True)
    urgency: Mapped[ActionUrgency] = mapped_column(
        Enum(ActionUrgency, name="action_urgency", create_constraint=True),
        default=ActionUrgency.this_week,
        nullable=False,
    )
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Relationships ────────────────────────────────────────────────────
    call: Mapped["Call"] = relationship("Call", back_populates="action_items")  # noqa: F821

    __table_args__ = (
        Index("ix_ai_call_urgency", "call_id", "urgency"),
        Index("ix_ai_completed", "completed"),
    )

    def __repr__(self) -> str:
        return f"<ActionItem {self.id} urgency={self.urgency.value} completed={self.completed}>"
