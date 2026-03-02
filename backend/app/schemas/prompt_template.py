"""Prompt template Pydantic schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PromptTemplateResponse(BaseModel):
    """Full prompt template response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str
    template_content: str
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CreatePromptTemplateRequest(BaseModel):
    """Create a new prompt template."""

    name: str = Field(..., max_length=100, description="Template identifier")
    description: str = Field(default="", description="Human-readable description")
    template_content: str = Field(..., description="Full Jinja2/text prompt template")


class UpdatePromptTemplateRequest(BaseModel):
    """Update an existing prompt template."""

    description: Optional[str] = Field(default=None, description="Human-readable description")
    template_content: Optional[str] = Field(default=None, description="Updated prompt template content")


class PromptTemplateListResponse(BaseModel):
    """List of prompt templates."""

    items: List[PromptTemplateResponse]
