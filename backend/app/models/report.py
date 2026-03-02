"""Weekly report snapshots."""

import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ReportStatus(str, enum.Enum):
    """Generation lifecycle of a weekly report."""

    pending = "pending"
    generating = "generating"
    completed = "completed"
    failed = "failed"


class WeeklyReport(TimestampMixin, Base):
    """Snapshot of a generated weekly performance report."""

    __tablename__ = "weekly_reports"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    report_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status", create_constraint=True),
        default=ReportStatus.pending,
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="weekly_reports")  # noqa: F821
    generator: Mapped["User | None"] = relationship("User")  # noqa: F821

    __table_args__ = (
        Index("ix_wr_tenant_week", "tenant_id", "week_start", "week_end"),
        Index("ix_wr_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<WeeklyReport {self.week_start} – {self.week_end} status={self.status.value}>"
