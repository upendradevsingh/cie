"""Lead management routes — lead-level aggregated views."""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.rls import set_tenant_context
from app.db.session import get_db_with_tenant
from app.models.lead import Lead
from app.models.user import User
from app.services.auth import get_current_active_user

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get(
    "",
    summary="List all leads with aggregated data",
)
def list_leads(
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    classification: str | None = Query(
        default=None, description="Filter by intent classification (hot/warm/cold)"
    ),
    urgency: str | None = Query(
        default=None, description="Filter by follow-up urgency"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> List[dict]:
    """Return a list of leads with aggregated call data."""
    set_tenant_context(db, current_user.tenant_id)

    query = db.query(Lead).filter(Lead.tenant_id == current_user.tenant_id)

    if classification:
        query = query.filter(Lead.latest_intent_classification == classification.lower())

    if urgency:
        query = query.filter(Lead.follow_up_urgency == urgency.lower())

    leads = (
        query.order_by(Lead.latest_call_date.desc().nulls_last())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return [
        {
            "id": str(lead.id),
            "lead_id": lead.lead_id,
            "lead_name": lead.lead_name,
            "lead_phone": lead.lead_phone,
            "lead_email": lead.lead_email,
            "source": lead.source,
            "total_calls": lead.total_calls,
            "avg_quality_score": round(lead.avg_quality_score, 1)
            if lead.avg_quality_score
            else None,
            "avg_intent_score": round(lead.avg_intent_score, 1)
            if lead.avg_intent_score
            else None,
            "latest_intent_classification": lead.latest_intent_classification,
            "quality_trend": lead.quality_trend,
            "first_call_date": lead.first_call_date.isoformat()
            if lead.first_call_date
            else None,
            "latest_call_date": lead.latest_call_date.isoformat()
            if lead.latest_call_date
            else None,
            "follow_up_urgency": lead.follow_up_urgency,
            "pending_action_items": lead.pending_action_items,
            "completed_action_items": lead.completed_action_items,
        }
        for lead in leads
    ]


@router.get(
    "/{lead_id}",
    summary="Get detailed lead view with full aggregated data",
)
def get_lead(
    lead_id: str,
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Return complete lead details with all aggregated insights."""
    set_tenant_context(db, current_user.tenant_id)

    lead = (
        db.query(Lead)
        .filter(Lead.tenant_id == current_user.tenant_id, Lead.lead_id == lead_id)
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found",
        )

    return {
        "id": str(lead.id),
        "lead_id": lead.lead_id,
        "lead_name": lead.lead_name,
        "lead_phone": lead.lead_phone,
        "lead_email": lead.lead_email,
        "source": lead.source,
        "total_calls": lead.total_calls,
        "avg_quality_score": round(lead.avg_quality_score, 1)
        if lead.avg_quality_score
        else None,
        "avg_intent_score": round(lead.avg_intent_score, 1)
        if lead.avg_intent_score
        else None,
        "latest_intent_classification": lead.latest_intent_classification,
        "quality_trend": lead.quality_trend,
        "first_call_date": lead.first_call_date.isoformat()
        if lead.first_call_date
        else None,
        "latest_call_date": lead.latest_call_date.isoformat()
        if lead.latest_call_date
        else None,
        "top_objections": lead.top_objections or [],
        "all_tags": lead.all_tags or [],
        "key_pain_points": lead.key_pain_points or [],
        "competitors_mentioned": lead.competitors_mentioned or [],
        "bant": {
            "budget_score": lead.latest_budget_score,
            "authority_score": lead.latest_authority_score,
            "need_score": lead.latest_need_score,
            "timeline_score": lead.latest_timeline_score,
        },
        "latest_persona_type": lead.latest_persona_type,
        "follow_up_urgency": lead.follow_up_urgency,
        "pending_action_items": lead.pending_action_items,
        "completed_action_items": lead.completed_action_items,
        "recommended_next_steps": lead.recommended_next_steps or [],
        "custom_data": lead.custom_data or {},
    }
