"""Persona type CRUD routes."""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.rls import set_tenant_context
from app.db.session import get_db_with_tenant
from app.models.persona import PersonaType
from app.models.user import User
from app.schemas.persona import (
    PersonaTypeCreate,
    PersonaTypeResponse,
    PersonaTypeUpdate,
)
from app.services.auth import get_current_active_user, require_role

router = APIRouter(prefix="/persona-types", tags=["Persona Types"])


# ---------------------------------------------------------------------------
# GET /persona-types
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=List[PersonaTypeResponse],
    summary="List all persona types for the current tenant",
)
def list_persona_types(
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    include_inactive: bool = False,
) -> List[PersonaTypeResponse]:
    """Return persona type definitions configured for the tenant.

    By default only active types are returned.  Pass
    ``include_inactive=true`` to include soft-deleted entries.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    query = db.query(PersonaType).filter(
        # RLS enforces tenant isolation; filter kept as defense-in-depth
        PersonaType.tenant_id == current_user.tenant_id,
    )

    if not include_inactive:
        query = query.filter(PersonaType.is_active.is_(True))

    types = query.order_by(PersonaType.created_at).all()
    return [PersonaTypeResponse.model_validate(t) for t in types]


# ---------------------------------------------------------------------------
# POST /persona-types
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=PersonaTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new persona type",
)
def create_persona_type(
    body: PersonaTypeCreate,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> PersonaTypeResponse:
    """Create a new persona type for the tenant.

    A persona type describes a buyer archetype (e.g. "Budget-Conscious
    Decision Maker") and optionally includes a BANT profile template.
    Only admins can create persona types.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    persona_type = PersonaType(
        tenant_id=current_user.tenant_id,
        name=body.name,
        description=body.description,
        bant_profile=body.bant_profile,
        is_active=True,
    )
    db.add(persona_type)
    db.commit()
    db.refresh(persona_type)

    return PersonaTypeResponse.model_validate(persona_type)


# ---------------------------------------------------------------------------
# PUT /persona-types/{id}
# ---------------------------------------------------------------------------


@router.put(
    "/{persona_type_id}",
    response_model=PersonaTypeResponse,
    summary="Update a persona type",
)
def update_persona_type(
    persona_type_id: UUID,
    body: PersonaTypeUpdate,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> PersonaTypeResponse:
    """Update an existing persona type. Only admins can modify persona types."""
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    persona_type = (
        db.query(PersonaType)
        .filter(
            PersonaType.id == persona_type_id,
            # RLS enforces tenant isolation; filter kept as defense-in-depth
            PersonaType.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if persona_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona type not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(persona_type, field, value)

    db.commit()
    db.refresh(persona_type)

    return PersonaTypeResponse.model_validate(persona_type)


# ---------------------------------------------------------------------------
# DELETE /persona-types/{id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{persona_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a persona type",
)
def delete_persona_type(
    persona_type_id: UUID,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> None:
    """Soft-delete a persona type by setting ``is_active=False``.

    Historical persona classifications are preserved.
    Only admins can delete persona types.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    persona_type = (
        db.query(PersonaType)
        .filter(
            PersonaType.id == persona_type_id,
            # RLS enforces tenant isolation; filter kept as defense-in-depth
            PersonaType.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if persona_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona type not found",
        )

    persona_type.is_active = False
    db.commit()
