"""Quality parameter CRUD routes and default seeding."""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.rls import set_tenant_context
from app.db.session import get_db_with_tenant
from app.models.quality import QualityParameter
from app.models.user import User
from app.schemas.quality import (
    QualityParameterCreate,
    QualityParameterResponse,
    QualityParameterUpdate,
)
from app.services.auth import get_current_active_user, require_role

router = APIRouter(prefix="/quality-parameters", tags=["Quality Parameters"])


# ---------------------------------------------------------------------------
# Default quality parameters shipped with SalesLens
# ---------------------------------------------------------------------------

DEFAULT_QUALITY_PARAMETERS: List[dict] = [
    {
        "name": "Opening & Greeting",
        "description": (
            "Evaluates whether the agent introduced themselves properly, "
            "stated the purpose of the call, and set a positive tone with "
            "appropriate energy and enthusiasm."
        ),
        "weight": 0.06,
        "category": "Communication",
        "display_order": 1,
    },
    {
        "name": "Need Discovery",
        "description": (
            "Assesses whether the agent asked probing open-ended questions "
            "to understand the prospect's requirements, pain points, and "
            "current situation before pitching."
        ),
        "weight": 0.08,
        "category": "Sales Technique",
        "display_order": 2,
    },
    {
        "name": "Product Knowledge",
        "description": (
            "Measures the agent's accuracy when describing product features, "
            "benefits, and differentiators. Penalizes incorrect or vague "
            "information."
        ),
        "weight": 0.08,
        "category": "Knowledge",
        "display_order": 3,
    },
    {
        "name": "Objection Handling",
        "description": (
            "Evaluates how effectively the agent acknowledged, empathized "
            "with, and addressed customer objections or concerns with clear "
            "rebuttals and evidence."
        ),
        "weight": 0.09,
        "category": "Sales Technique",
        "display_order": 4,
    },
    {
        "name": "Pricing Discussion",
        "description": (
            "Assesses whether pricing was presented transparently, framed "
            "around value, and whether the agent handled price objections "
            "without unnecessary discounting."
        ),
        "weight": 0.07,
        "category": "Sales Technique",
        "display_order": 5,
    },
    {
        "name": "Urgency Creation",
        "description": (
            "Measures the agent's ability to create genuine urgency through "
            "time-sensitive offers, limited availability, or highlighting "
            "the cost of inaction."
        ),
        "weight": 0.06,
        "category": "Sales Technique",
        "display_order": 6,
    },
    {
        "name": "Next Steps",
        "description": (
            "Evaluates whether the agent established clear, specific next "
            "steps with timelines and confirmed the prospect's commitment "
            "to those steps."
        ),
        "weight": 0.07,
        "category": "Process",
        "display_order": 7,
    },
    {
        "name": "Call Control",
        "description": (
            "Assesses the agent's ability to manage the conversation flow, "
            "keep it on track, redirect tangents, and cover all necessary "
            "topics within a reasonable time."
        ),
        "weight": 0.06,
        "category": "Communication",
        "display_order": 8,
    },
    {
        "name": "Active Listening",
        "description": (
            "Measures whether the agent demonstrated active listening by "
            "acknowledging customer statements, paraphrasing concerns, and "
            "asking relevant follow-up questions."
        ),
        "weight": 0.07,
        "category": "Communication",
        "display_order": 9,
    },
    {
        "name": "Closing Technique",
        "description": (
            "Evaluates whether the agent used an effective closing technique, "
            "asked for commitment or the sale, and handled last-minute "
            "hesitation confidently."
        ),
        "weight": 0.08,
        "category": "Sales Technique",
        "display_order": 10,
    },
    {
        "name": "Compliance",
        "description": (
            "Checks whether the agent made all mandatory disclosures, avoided "
            "false promises or misleading claims, and adhered to regulatory "
            "and company policy requirements."
        ),
        "weight": 0.06,
        "category": "Process",
        "display_order": 11,
    },
    {
        "name": "Tone & Professionalism",
        "description": (
            "Assesses the agent's overall tone, politeness, professionalism, "
            "and emotional control throughout the call, especially during "
            "difficult moments."
        ),
        "weight": 0.06,
        "category": "Communication",
        "display_order": 12,
    },
    {
        "name": "Rapport Building",
        "description": (
            "Measures the agent's ability to build personal connection and "
            "trust through small talk, empathy, humor where appropriate, "
            "and genuine interest in the prospect."
        ),
        "weight": 0.05,
        "category": "Communication",
        "display_order": 13,
    },
    {
        "name": "Competitor Handling",
        "description": (
            "Evaluates how the agent addressed competitor mentions -- whether "
            "they acknowledged competitors respectfully while clearly "
            "differentiating their own product's advantages."
        ),
        "weight": 0.06,
        "category": "Knowledge",
        "display_order": 14,
    },
    {
        "name": "Documentation",
        "description": (
            "Assesses whether the agent captured key information during the "
            "call (requirements, budget, timeline, decision makers) and "
            "confirmed details with the prospect."
        ),
        "weight": 0.05,
        "category": "Process",
        "display_order": 15,
    },
]


# ---------------------------------------------------------------------------
# GET /quality-parameters
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=List[QualityParameterResponse],
    summary="List all quality parameters for the current tenant",
)
def list_quality_parameters(
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    include_inactive: bool = False,
) -> List[QualityParameterResponse]:
    """Return quality scoring parameters configured for the tenant.

    By default only active parameters are returned.  Pass
    ``include_inactive=true`` to include soft-deleted entries.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    query = db.query(QualityParameter).filter(
        # RLS enforces tenant isolation; filter kept as defense-in-depth
        QualityParameter.tenant_id == current_user.tenant_id,
    )

    if not include_inactive:
        query = query.filter(QualityParameter.is_active.is_(True))

    params = query.order_by(QualityParameter.display_order).all()
    return [QualityParameterResponse.model_validate(p) for p in params]


# ---------------------------------------------------------------------------
# POST /quality-parameters
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=QualityParameterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new quality parameter",
)
def create_quality_parameter(
    body: QualityParameterCreate,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> QualityParameterResponse:
    """Create a new quality scoring parameter for the tenant.

    Only admins can create parameters.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    param = QualityParameter(
        tenant_id=current_user.tenant_id,
        name=body.name,
        description=body.description,
        weight=body.weight,
        category=body.category,
        display_order=body.display_order,
        is_active=True,
    )
    db.add(param)
    db.commit()
    db.refresh(param)

    return QualityParameterResponse.model_validate(param)


# ---------------------------------------------------------------------------
# PUT /quality-parameters/{id}
# ---------------------------------------------------------------------------


@router.put(
    "/{param_id}",
    response_model=QualityParameterResponse,
    summary="Update a quality parameter",
)
def update_quality_parameter(
    param_id: UUID,
    body: QualityParameterUpdate,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> QualityParameterResponse:
    """Update an existing quality parameter. Only admins can modify parameters."""
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    param = (
        db.query(QualityParameter)
        .filter(
            QualityParameter.id == param_id,
            # RLS enforces tenant isolation; filter kept as defense-in-depth
            QualityParameter.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if param is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quality parameter not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(param, field, value)

    db.commit()
    db.refresh(param)

    return QualityParameterResponse.model_validate(param)


# ---------------------------------------------------------------------------
# DELETE /quality-parameters/{id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{param_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a quality parameter",
)
def delete_quality_parameter(
    param_id: UUID,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> None:
    """Soft-delete a quality parameter by setting ``is_active=False``.

    The parameter and its historical scores are preserved for reporting.
    Only admins can delete parameters.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    param = (
        db.query(QualityParameter)
        .filter(
            QualityParameter.id == param_id,
            # RLS enforces tenant isolation; filter kept as defense-in-depth
            QualityParameter.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if param is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quality parameter not found",
        )

    param.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# POST /quality-parameters/seed-defaults
# ---------------------------------------------------------------------------


@router.post(
    "/seed-defaults",
    response_model=List[QualityParameterResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Seed default quality parameters for the tenant",
)
def seed_defaults(
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> List[QualityParameterResponse]:
    """Populate the tenant with the built-in set of 15 default quality
    parameters.

    This is idempotent -- existing parameters with matching names are
    skipped.  Only admins can seed defaults.
    """
    # Set RLS tenant context for this transaction
    set_tenant_context(db, current_user.tenant_id)

    existing_names = {
        p.name
        for p in db.query(QualityParameter.name)
        # RLS enforces tenant isolation; filter kept as defense-in-depth
        .filter(QualityParameter.tenant_id == current_user.tenant_id)
        .all()
    }

    created: List[QualityParameter] = []
    for defaults in DEFAULT_QUALITY_PARAMETERS:
        if defaults["name"] in existing_names:
            continue
        param = QualityParameter(
            tenant_id=current_user.tenant_id,
            name=defaults["name"],
            description=defaults["description"],
            weight=defaults["weight"],
            category=defaults["category"],
            display_order=defaults["display_order"],
            is_active=True,
        )
        db.add(param)
        created.append(param)

    db.commit()
    for p in created:
        db.refresh(p)

    return [QualityParameterResponse.model_validate(p) for p in created]
