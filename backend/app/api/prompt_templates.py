"""Prompt template CRUD routes."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.rls import set_tenant_context
from app.db.session import get_db_with_tenant
from app.models.prompt_template import PromptTemplate
from app.models.user import User
from app.schemas.prompt_template import (
    CreatePromptTemplateRequest,
    PromptTemplateResponse,
    UpdatePromptTemplateRequest,
)
from app.services.auth import get_current_active_user, require_role

router = APIRouter(prefix="/prompt-templates", tags=["Prompt Templates"])

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


# ---------------------------------------------------------------------------
# GET /prompt-templates
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=List[PromptTemplateResponse],
    summary="List prompt templates for the tenant",
)
def list_prompt_templates(
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> List[PromptTemplateResponse]:
    """Return all prompt templates for the current tenant."""
    set_tenant_context(db, current_user.tenant_id)

    templates = (
        db.query(PromptTemplate)
        .filter(PromptTemplate.tenant_id == current_user.tenant_id)
        .order_by(PromptTemplate.name)
        .all()
    )
    return [PromptTemplateResponse.model_validate(t) for t in templates]


# ---------------------------------------------------------------------------
# GET /prompt-templates/{template_id}
# ---------------------------------------------------------------------------


@router.get(
    "/{template_id}",
    response_model=PromptTemplateResponse,
    summary="Get a single prompt template",
)
def get_prompt_template(
    template_id: UUID,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> PromptTemplateResponse:
    """Return a single prompt template by ID."""
    set_tenant_context(db, current_user.tenant_id)

    template = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.id == template_id,
            PromptTemplate.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt template not found",
        )
    return PromptTemplateResponse.model_validate(template)


# ---------------------------------------------------------------------------
# PUT /prompt-templates/{template_id}
# ---------------------------------------------------------------------------


@router.put(
    "/{template_id}",
    response_model=PromptTemplateResponse,
    summary="Update a prompt template (auto-increments version)",
)
def update_prompt_template(
    template_id: UUID,
    body: UpdatePromptTemplateRequest,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> PromptTemplateResponse:
    """Update a prompt template. Version is auto-incremented on content change."""
    set_tenant_context(db, current_user.tenant_id)

    template = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.id == template_id,
            PromptTemplate.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt template not found",
        )

    if body.description is not None:
        template.description = body.description

    if body.template_content is not None:
        template.template_content = body.template_content
        template.version += 1

    template.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(template)

    return PromptTemplateResponse.model_validate(template)


# ---------------------------------------------------------------------------
# POST /prompt-templates/seed
# ---------------------------------------------------------------------------


@router.post(
    "/seed",
    response_model=List[PromptTemplateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Seed default prompt templates from Jinja2 files",
)
def seed_prompt_templates(
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> List[PromptTemplateResponse]:
    """Seed the default call_analysis prompt template from the Jinja2 file."""
    set_tenant_context(db, current_user.tenant_id)

    results = []
    template_file = _PROMPTS_DIR / "call_analysis.jinja2"

    if not template_file.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default prompt template file not found on server",
        )

    content = template_file.read_text(encoding="utf-8")

    # Check if already seeded
    existing = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.tenant_id == current_user.tenant_id,
            PromptTemplate.name == "call_analysis",
        )
        .first()
    )

    if existing:
        # Update to latest default content
        existing.template_content = content
        existing.version += 1
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        results.append(existing)
    else:
        template = PromptTemplate(
            tenant_id=current_user.tenant_id,
            name="call_analysis",
            description="Main call analysis prompt — extracts quality scores, intent signals, persona, action items, escalation keywords, sentiment, and call tags.",
            template_content=content,
            version=1,
            is_active=True,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        results.append(template)

    return [PromptTemplateResponse.model_validate(t) for t in results]


# ---------------------------------------------------------------------------
# POST /prompt-templates/{template_id}/reset
# ---------------------------------------------------------------------------


@router.post(
    "/{template_id}/reset",
    response_model=PromptTemplateResponse,
    summary="Reset a prompt template to its default content",
)
def reset_prompt_template(
    template_id: UUID,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> PromptTemplateResponse:
    """Reset a prompt template to the default Jinja2 file content."""
    set_tenant_context(db, current_user.tenant_id)

    template = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.id == template_id,
            PromptTemplate.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt template not found",
        )

    # Load default content from file
    template_file = _PROMPTS_DIR / f"{template.name}.jinja2"
    if not template_file.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Default template file for '{template.name}' not found",
        )

    template.template_content = template_file.read_text(encoding="utf-8")
    template.version += 1
    template.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(template)

    return PromptTemplateResponse.model_validate(template)
