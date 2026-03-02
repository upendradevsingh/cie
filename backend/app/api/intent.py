"""Intent signal CRUD routes and default seeding."""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.intent import IntentSignal
from app.models.user import User
from app.schemas.intent import (
    IntentSignalCreate,
    IntentSignalResponse,
    IntentSignalUpdate,
)
from app.services.auth import get_current_active_user, require_role

router = APIRouter(prefix="/intent-signals", tags=["Intent Signals"])


# ---------------------------------------------------------------------------
# Default intent signals shipped with SalesLens
# ---------------------------------------------------------------------------

DEFAULT_INTENT_SIGNALS: List[dict] = [
    {
        "name": "Budget Mentioned",
        "description": (
            "The lead explicitly mentioned a budget range, spending capacity, "
            "or financial constraints relevant to the purchase."
        ),
    },
    {
        "name": "Timeline Discussed",
        "description": (
            "The lead discussed a specific timeframe for making a decision, "
            "starting implementation, or needing the solution by a certain date."
        ),
    },
    {
        "name": "Decision Maker Identified",
        "description": (
            "The call revealed who the decision maker is -- whether it's the "
            "person on the call, a manager, a committee, or another stakeholder."
        ),
    },
    {
        "name": "Competitor Comparison",
        "description": (
            "The lead mentioned comparing the product with a competitor's "
            "offering, asked about differentiators, or referenced another vendor."
        ),
    },
    {
        "name": "Specific Requirements Stated",
        "description": (
            "The lead articulated specific needs, use cases, feature requests, "
            "or integration requirements that indicate serious consideration."
        ),
    },
    {
        "name": "Follow-up Requested",
        "description": (
            "The lead explicitly requested a follow-up call, demo, proposal, "
            "documentation, or any form of continued engagement."
        ),
    },
    {
        "name": "Pricing Asked",
        "description": (
            "The lead asked about pricing, packages, discounts, payment terms, "
            "or any cost-related information."
        ),
    },
    {
        "name": "Objections Raised",
        "description": (
            "The lead raised explicit concerns, hesitations, or objections "
            "about the product, pricing, timeline, or switching costs."
        ),
    },
]


# ---------------------------------------------------------------------------
# GET /intent-signals
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=List[IntentSignalResponse],
    summary="List all intent signals for the current tenant",
)
def list_intent_signals(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    include_inactive: bool = False,
) -> List[IntentSignalResponse]:
    """Return intent signal definitions configured for the tenant.

    By default only active signals are returned.  Pass
    ``include_inactive=true`` to include soft-deleted entries.
    """
    query = db.query(IntentSignal).filter(
        IntentSignal.tenant_id == current_user.tenant_id,
    )

    if not include_inactive:
        query = query.filter(IntentSignal.is_active.is_(True))

    signals = query.order_by(IntentSignal.created_at).all()
    return [IntentSignalResponse.model_validate(s) for s in signals]


# ---------------------------------------------------------------------------
# POST /intent-signals
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=IntentSignalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new intent signal",
)
def create_intent_signal(
    body: IntentSignalCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> IntentSignalResponse:
    """Create a new intent signal definition for the tenant.

    Only admins can create signals.
    """
    signal = IntentSignal(
        tenant_id=current_user.tenant_id,
        name=body.name,
        description=body.description,
        is_active=True,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)

    return IntentSignalResponse.model_validate(signal)


# ---------------------------------------------------------------------------
# PUT /intent-signals/{id}
# ---------------------------------------------------------------------------


@router.put(
    "/{signal_id}",
    response_model=IntentSignalResponse,
    summary="Update an intent signal",
)
def update_intent_signal(
    signal_id: UUID,
    body: IntentSignalUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> IntentSignalResponse:
    """Update an existing intent signal definition. Only admins can modify signals."""
    signal = (
        db.query(IntentSignal)
        .filter(
            IntentSignal.id == signal_id,
            IntentSignal.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if signal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intent signal not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(signal, field, value)

    db.commit()
    db.refresh(signal)

    return IntentSignalResponse.model_validate(signal)


# ---------------------------------------------------------------------------
# DELETE /intent-signals/{id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{signal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete an intent signal",
)
def delete_intent_signal(
    signal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> None:
    """Soft-delete an intent signal by setting ``is_active=False``.

    Historical detection results are preserved. Only admins can delete signals.
    """
    signal = (
        db.query(IntentSignal)
        .filter(
            IntentSignal.id == signal_id,
            IntentSignal.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if signal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intent signal not found",
        )

    signal.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# POST /intent-signals/seed-defaults
# ---------------------------------------------------------------------------


@router.post(
    "/seed-defaults",
    response_model=List[IntentSignalResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Seed default intent signals for the tenant",
)
def seed_defaults(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["admin"]))],
) -> List[IntentSignalResponse]:
    """Populate the tenant with the built-in set of 8 default intent signals.

    Idempotent -- signals with matching names are skipped.
    Only admins can seed defaults.
    """
    existing_names = {
        s.name
        for s in db.query(IntentSignal.name)
        .filter(IntentSignal.tenant_id == current_user.tenant_id)
        .all()
    }

    created: List[IntentSignal] = []
    for defaults in DEFAULT_INTENT_SIGNALS:
        if defaults["name"] in existing_names:
            continue
        signal = IntentSignal(
            tenant_id=current_user.tenant_id,
            name=defaults["name"],
            description=defaults["description"],
            is_active=True,
        )
        db.add(signal)
        created.append(signal)

    db.commit()
    for s in created:
        db.refresh(s)

    return [IntentSignalResponse.model_validate(s) for s in created]
