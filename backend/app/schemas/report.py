"""Weekly report schemas."""

from datetime import date, datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WeeklyReportRequest(BaseModel):
    """Request to generate a weekly report for a given time window."""

    week_start: date = Field(
        ...,
        description="Start date (Monday) of the reporting week",
    )
    week_end: Optional[date] = Field(
        default=None,
        description=(
            "End date (Sunday) of the reporting week. "
            "If omitted, defaults to week_start + 6 days."
        ),
    )

    @field_validator("week_end")
    @classmethod
    def validate_date_range(cls, v: Optional[date], info: Any) -> Optional[date]:
        if v is not None and "week_start" in info.data:
            week_start = info.data["week_start"]
            if v < week_start:
                raise ValueError("week_end must not be before week_start")
        return v


class WeeklyReportResponse(BaseModel):
    """Generated weekly report as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    week_start: date
    week_end: date
    report_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Full report payload (team stats, per-agent breakdown, highlights)",
    )
    status: str = Field(
        ...,
        description="Report generation status: pending, generating, completed, failed",
    )
    created_at: datetime
