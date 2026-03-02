"""Data capture question configuration routes."""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.rls import set_tenant_context
from app.db.session import get_db_with_tenant
from app.models.data_capture import DataCaptureQuestion
from app.models.user import User
from app.services.auth import get_current_active_user, require_role

router = APIRouter(prefix="/data-capture-questions", tags=["Data Capture"])


@router.get(
    "",
    summary="List all data capture questions",
)
def list_data_capture_questions(
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    active_only: bool = True,
) -> List[dict]:
    """Return all data capture questions for the tenant."""
    set_tenant_context(db, current_user.tenant_id)

    query = db.query(DataCaptureQuestion).filter(
        DataCaptureQuestion.tenant_id == current_user.tenant_id
    )

    if active_only:
        query = query.filter(DataCaptureQuestion.is_active.is_(True))

    questions = query.order_by(DataCaptureQuestion.display_order).all()

    return [
        {
            "id": str(q.id),
            "question": q.question,
            "field_name": q.field_name,
            "expected_type": q.expected_type,
            "description": q.description,
            "display_order": q.display_order,
            "is_active": q.is_active,
            "category": q.category,
            "created_at": q.created_at.isoformat(),
        }
        for q in questions
    ]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new data capture question",
)
def create_data_capture_question(
    question_data: dict,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> dict:
    """Create a new data capture question (admin only)."""
    set_tenant_context(db, current_user.tenant_id)

    # Validate max 10 active questions per tenant
    active_count = (
        db.query(DataCaptureQuestion)
        .filter(
            DataCaptureQuestion.tenant_id == current_user.tenant_id,
            DataCaptureQuestion.is_active.is_(True),
        )
        .count()
    )

    if active_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 active data capture questions allowed per tenant",
        )

    question = DataCaptureQuestion(
        tenant_id=current_user.tenant_id,
        question=question_data["question"],
        field_name=question_data["field_name"],
        expected_type=question_data.get("expected_type", "text"),
        description=question_data.get("description"),
        display_order=question_data.get("display_order", active_count),
        category=question_data.get("category"),
    )

    db.add(question)
    db.commit()
    db.refresh(question)

    return {
        "id": str(question.id),
        "question": question.question,
        "field_name": question.field_name,
        "expected_type": question.expected_type,
        "description": question.description,
        "display_order": question.display_order,
        "is_active": question.is_active,
        "category": question.category,
    }


@router.put(
    "/{question_id}",
    summary="Update a data capture question",
)
def update_data_capture_question(
    question_id: UUID,
    question_data: dict,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> dict:
    """Update an existing data capture question (admin only)."""
    set_tenant_context(db, current_user.tenant_id)

    question = (
        db.query(DataCaptureQuestion)
        .filter(
            DataCaptureQuestion.id == question_id,
            DataCaptureQuestion.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data capture question not found",
        )

    # Update fields
    for key, value in question_data.items():
        if hasattr(question, key) and key not in ("id", "tenant_id", "created_at"):
            setattr(question, key, value)

    db.commit()
    db.refresh(question)

    return {
        "id": str(question.id),
        "question": question.question,
        "field_name": question.field_name,
        "expected_type": question.expected_type,
        "description": question.description,
        "display_order": question.display_order,
        "is_active": question.is_active,
        "category": question.category,
    }


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a data capture question",
)
def delete_data_capture_question(
    question_id: UUID,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> None:
    """Delete a data capture question (admin only)."""
    set_tenant_context(db, current_user.tenant_id)

    question = (
        db.query(DataCaptureQuestion)
        .filter(
            DataCaptureQuestion.id == question_id,
            DataCaptureQuestion.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data capture question not found",
        )

    db.delete(question)
    db.commit()
