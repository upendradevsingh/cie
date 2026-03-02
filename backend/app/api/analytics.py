"""Analytics routes -- team performance, agent performance, trends, and leaderboard."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, cast, func, Float as SAFloat
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.call import Call, CallStatus, IntentClassification
from app.models.quality import CallQualityScore, QualityParameter
from app.models.user import User
from app.schemas.analytics import (
    AgentAnalytics,
    LeaderboardEntry,
    TeamAnalytics,
    TrendData,
)
from app.services.auth import get_current_active_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_date_range(
    date_from: Optional[datetime],
    date_to: Optional[datetime],
) -> tuple[datetime, datetime]:
    """Return sensible defaults when date range is not fully specified."""
    if date_to is None:
        date_to = datetime.now(timezone.utc)
    if date_from is None:
        date_from = date_to - timedelta(days=30)
    return date_from, date_to


# ---------------------------------------------------------------------------
# GET /analytics/team
# ---------------------------------------------------------------------------


@router.get(
    "/team",
    response_model=TeamAnalytics,
    summary="Team-level analytics overview",
)
def team_analytics(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    date_from: Optional[datetime] = Query(default=None, description="Period start"),
    date_to: Optional[datetime] = Query(default=None, description="Period end"),
) -> TeamAnalytics:
    """Return aggregated analytics for the entire team / tenant.

    Includes total calls, average scores, lead intent counts, calls by
    day, top agents, and score distribution.
    """
    date_from, date_to = _default_date_range(date_from, date_to)
    tenant_id = current_user.tenant_id

    # Base query for completed calls in the period
    base = (
        db.query(Call)
        .filter(
            Call.tenant_id == tenant_id,
            Call.created_at >= date_from,
            Call.created_at <= date_to,
        )
    )

    # Total calls (all statuses)
    total_calls = base.count()

    # Completed calls for score averages
    completed = base.filter(Call.status == CallStatus.completed)

    # Average quality score
    avg_score_result = completed.with_entities(
        func.avg(Call.overall_score)
    ).scalar()
    avg_quality_score = round(avg_score_result, 2) if avg_score_result else None

    # Intent classification counts
    hot_count = completed.filter(
        Call.intent_classification == IntentClassification.hot
    ).count()
    warm_count = completed.filter(
        Call.intent_classification == IntentClassification.warm
    ).count()
    cold_count = completed.filter(
        Call.intent_classification == IntentClassification.cold
    ).count()

    # Calls by day
    calls_by_day_raw = (
        base.with_entities(
            func.date_trunc("day", Call.created_at).label("day"),
            func.count(Call.id).label("count"),
        )
        .group_by("day")
        .order_by("day")
        .all()
    )
    calls_by_day = [
        TrendData(
            date=row.day.strftime("%Y-%m-%d") if hasattr(row.day, "strftime") else str(row.day),
            value=float(row.count),
            label="Calls",
        )
        for row in calls_by_day_raw
    ]

    # Top agents by average quality score (top 10)
    top_agents_raw = (
        completed.join(User, Call.agent_id == User.id)
        .with_entities(
            User.id.label("agent_id"),
            User.full_name.label("agent_name"),
            func.avg(Call.overall_score).label("avg_score"),
            func.count(Call.id).label("total"),
        )
        .group_by(User.id, User.full_name)
        .order_by(func.avg(Call.overall_score).desc())
        .limit(10)
        .all()
    )
    top_agents = [
        {
            "agent_id": str(row.agent_id),
            "agent_name": row.agent_name,
            "avg_quality_score": round(row.avg_score, 2) if row.avg_score else None,
            "total_calls": row.total,
        }
        for row in top_agents_raw
    ]

    # Score distribution (buckets of 20)
    score_distribution: Dict[str, int] = {
        "0-20": 0,
        "21-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0,
    }
    score_rows = (
        completed.with_entities(Call.overall_score)
        .filter(Call.overall_score.isnot(None))
        .all()
    )
    for (score,) in score_rows:
        if score <= 20:
            score_distribution["0-20"] += 1
        elif score <= 40:
            score_distribution["21-40"] += 1
        elif score <= 60:
            score_distribution["41-60"] += 1
        elif score <= 80:
            score_distribution["61-80"] += 1
        else:
            score_distribution["81-100"] += 1

    return TeamAnalytics(
        total_calls=total_calls,
        avg_quality_score=avg_quality_score,
        hot_leads_count=hot_count,
        warm_leads_count=warm_count,
        cold_leads_count=cold_count,
        calls_by_day=calls_by_day,
        top_agents=top_agents,
        score_distribution=score_distribution,
    )


# ---------------------------------------------------------------------------
# GET /analytics/agent/{agent_id}
# ---------------------------------------------------------------------------


@router.get(
    "/agent/{agent_id}",
    response_model=AgentAnalytics,
    summary="Per-agent performance analytics",
)
def agent_analytics(
    agent_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    date_from: Optional[datetime] = Query(default=None, description="Period start"),
    date_to: Optional[datetime] = Query(default=None, description="Period end"),
) -> AgentAnalytics:
    """Return detailed performance analytics for a specific agent.

    Includes total calls, average scores, score trends over time, top
    performing parameters, and areas for improvement.
    """
    date_from, date_to = _default_date_range(date_from, date_to)

    # Verify agent belongs to tenant
    agent = (
        db.query(User)
        .filter(
            User.id == agent_id,
            User.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found in this tenant",
        )

    # Base query
    base = (
        db.query(Call)
        .filter(
            Call.tenant_id == current_user.tenant_id,
            Call.agent_id == agent_id,
            Call.created_at >= date_from,
            Call.created_at <= date_to,
        )
    )

    total_calls = base.count()

    completed = base.filter(Call.status == CallStatus.completed)

    # Average scores
    avg_scores = completed.with_entities(
        func.avg(Call.overall_score).label("avg_quality"),
        func.avg(Call.lead_intent_score).label("avg_intent"),
    ).first()

    avg_quality_score = (
        round(avg_scores.avg_quality, 2) if avg_scores and avg_scores.avg_quality else None
    )
    avg_intent_score = (
        round(avg_scores.avg_intent, 2) if avg_scores and avg_scores.avg_intent else None
    )

    # Score trend over time (daily)
    trend_raw = (
        completed.with_entities(
            func.date_trunc("day", Call.created_at).label("day"),
            func.avg(Call.overall_score).label("avg_score"),
        )
        .filter(Call.overall_score.isnot(None))
        .group_by("day")
        .order_by("day")
        .all()
    )
    score_trend = [
        TrendData(
            date=row.day.strftime("%Y-%m-%d") if hasattr(row.day, "strftime") else str(row.day),
            value=round(row.avg_score, 2) if row.avg_score else 0,
            label="Quality Score",
        )
        for row in trend_raw
    ]

    # Top and bottom parameters
    completed_call_ids = [c.id for c in completed.with_entities(Call.id).all()]

    top_parameters: List[Dict] = []
    areas_for_improvement: List[Dict] = []

    if completed_call_ids:
        param_scores = (
            db.query(
                QualityParameter.name.label("parameter_name"),
                func.avg(CallQualityScore.score).label("avg_score"),
            )
            .join(CallQualityScore, CallQualityScore.parameter_id == QualityParameter.id)
            .filter(
                CallQualityScore.call_id.in_(completed_call_ids),
                QualityParameter.tenant_id == current_user.tenant_id,
                QualityParameter.is_active.is_(True),
            )
            .group_by(QualityParameter.name)
            .all()
        )

        sorted_asc = sorted(param_scores, key=lambda r: r.avg_score or 0)
        sorted_desc = sorted(param_scores, key=lambda r: r.avg_score or 0, reverse=True)

        top_parameters = [
            {
                "parameter_name": row.parameter_name,
                "avg_score": round(row.avg_score, 2) if row.avg_score else 0,
            }
            for row in sorted_desc[:5]
        ]

        areas_for_improvement = [
            {
                "parameter_name": row.parameter_name,
                "avg_score": round(row.avg_score, 2) if row.avg_score else 0,
            }
            for row in sorted_asc[:5]
        ]

    return AgentAnalytics(
        agent_id=agent.id,
        agent_name=agent.full_name,
        total_calls=total_calls,
        avg_quality_score=avg_quality_score,
        avg_intent_score=avg_intent_score,
        score_trend=score_trend,
        top_parameters=top_parameters,
        areas_for_improvement=areas_for_improvement,
    )


# ---------------------------------------------------------------------------
# GET /analytics/trends
# ---------------------------------------------------------------------------


@router.get(
    "/trends",
    response_model=List[TrendData],
    summary="Score trends over time",
)
def score_trends(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    date_from: Optional[datetime] = Query(default=None, description="Period start"),
    date_to: Optional[datetime] = Query(default=None, description="Period end"),
    aggregation: str = Query(
        default="daily",
        description="Aggregation granularity: daily or weekly",
    ),
) -> List[TrendData]:
    """Return quality score trends aggregated daily or weekly.

    Each data point contains the date and the average overall quality
    score for that period.
    """
    date_from, date_to = _default_date_range(date_from, date_to)

    trunc_unit = "week" if aggregation == "weekly" else "day"

    trend_raw = (
        db.query(
            func.date_trunc(trunc_unit, Call.created_at).label("period"),
            func.avg(Call.overall_score).label("avg_score"),
        )
        .filter(
            Call.tenant_id == current_user.tenant_id,
            Call.status == CallStatus.completed,
            Call.overall_score.isnot(None),
            Call.created_at >= date_from,
            Call.created_at <= date_to,
        )
        .group_by("period")
        .order_by("period")
        .all()
    )

    return [
        TrendData(
            date=row.period.strftime("%Y-%m-%d") if hasattr(row.period, "strftime") else str(row.period),
            value=round(row.avg_score, 2) if row.avg_score else 0,
            label="Avg Quality Score",
        )
        for row in trend_raw
    ]


# ---------------------------------------------------------------------------
# GET /analytics/leaderboard
# ---------------------------------------------------------------------------


@router.get(
    "/leaderboard",
    response_model=List[LeaderboardEntry],
    summary="Agent leaderboard ranked by quality score",
)
def leaderboard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    date_from: Optional[datetime] = Query(default=None, description="Period start"),
    date_to: Optional[datetime] = Query(default=None, description="Period end"),
    limit: int = Query(default=20, ge=1, le=100, description="Max entries to return"),
) -> List[LeaderboardEntry]:
    """Return a ranked leaderboard of agents ordered by average quality score.

    Each entry includes total calls, average quality and intent scores,
    hot lead count, and rank position.
    """
    date_from, date_to = _default_date_range(date_from, date_to)

    rows = (
        db.query(
            User.id.label("agent_id"),
            User.full_name.label("agent_name"),
            func.count(Call.id).label("total_calls"),
            func.avg(Call.overall_score).label("avg_quality_score"),
            func.avg(Call.lead_intent_score).label("avg_intent_score"),
            func.sum(
                case(
                    (Call.intent_classification == IntentClassification.hot, 1),
                    else_=0,
                )
            ).label("hot_leads_count"),
        )
        .join(Call, Call.agent_id == User.id)
        .filter(
            User.tenant_id == current_user.tenant_id,
            Call.tenant_id == current_user.tenant_id,
            Call.status == CallStatus.completed,
            Call.created_at >= date_from,
            Call.created_at <= date_to,
        )
        .group_by(User.id, User.full_name)
        .order_by(func.avg(Call.overall_score).desc().nulls_last())
        .limit(limit)
        .all()
    )

    return [
        LeaderboardEntry(
            agent_id=row.agent_id,
            agent_name=row.agent_name,
            total_calls=row.total_calls,
            avg_quality_score=round(row.avg_quality_score, 2) if row.avg_quality_score else None,
            avg_intent_score=round(row.avg_intent_score, 2) if row.avg_intent_score else None,
            hot_leads_count=row.hot_leads_count or 0,
            rank=idx + 1,
        )
        for idx, row in enumerate(rows)
    ]
