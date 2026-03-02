"""Action item schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActionItemResponse(BaseModel):
    """Action item / next step extracted from a call."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    description: str = Field(
        ...,
        description="What needs to be done",
    )
    category: Optional[str] = Field(
        default=None,
        description="Category (e.g. 'follow_up', 'send_info', 'schedule_demo', 'internal')",
    )
    urgency: Optional[str] = Field(
        default=None,
        description="Urgency level: immediate, this_week, next_week, nurture",
    )
    completed: bool = Field(
        default=False,
        description="Whether this action item has been marked as done",
    )

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"immediate", "this_week", "next_week", "nurture"}
        if v not in allowed:
            raise ValueError(f"urgency must be one of {allowed}, got '{v}'")
        return v


class ActionItemUpdate(BaseModel):
    """Payload for updating an action item (currently only completion toggle)."""

    completed: Optional[bool] = Field(
        default=None,
        description="Mark action item as completed or not",
    )
