from typing import Any, Optional

from pydantic import BaseModel


class ProfileAttributeSchema(BaseModel):
    name: str
    type: str
    required: bool = False
    values: Optional[list[str]] = None
    min: Optional[float] = None
    max: Optional[float] = None


class ExtractionTypeSchema(BaseModel):
    enabled: bool = True
    confidence_threshold: float = 0.75
    description: str = ""
    prompt_hint: Optional[str] = None
    attributes: list[ProfileAttributeSchema] = []


class ProfileLLMSchema(BaseModel):
    model: str = "gpt-5-mini"
    temperature: float = 0.15
    max_tokens: int = 2048
    fallback_model: Optional[str] = None


class ProfileSummarySchema(BaseModel):
    enabled: bool = True
    max_length: int = 200
    style: str = "concise"


class ProfileResponse(BaseModel):
    profile_id: str
    version: str
    display_name: str
    description: str
    llm: ProfileLLMSchema
    extraction_types: dict[str, ExtractionTypeSchema]
    summary: Optional[ProfileSummarySchema] = None
