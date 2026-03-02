"""Analytics routes -- team performance, agent performance, trends, and leaderboard."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, cast, func, Float as SAFloat
from sqlalchemy.orm import Session

from app.db.rls import set_tenant_context
from app.db.session import get_db_with_tenant
from app.models.call import Call, CallStatus, IntentClassification
from app.models.quality import CallQualityScore, QualityParameter
from app.models.user import User
from app.schemas.analytics import (
    AgentAnalytics,
    AgentComparisonItem,
    AnalyticsDataResponse,
    CallListItemResponse,
    CallTrend,
    ConversionFunnelStage,
    DashboardStats,
    HotLeadItem,
    LeaderboardEntry,
    LeadClassificationItem,
    ParameterTrend,
    ScoreDistribution,
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
    """Return sensible defaults when date range is not fully specified.

    When ``date_to`` has no time component (midnight), it is adjusted to
    the end of that day so that all calls on that date are included.
    """
    if date_to is None:
        date_to = datetime.now(timezone.utc)
    elif date_to.hour == 0 and date_to.minute == 0 and date_to.second == 0:
        date_to = date_to.replace(hour=23, minute=59, second=59)
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
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    date_from: Optional[datetime] = Query(default=None, description="Period start"),
    date_to: Optional[datetime] = Query(default=None, description="Period end"),
) -> TeamAnalytics:
    """Return aggregated analytics for the entire team / tenant.

    Structure matches the frontend TeamAnalytics TypeScript interface.
    """
    set_tenant_context(db, current_user.tenant_id)

    date_from, date_to = _default_date_range(date_from, date_to)
    tenant_id = current_user.tenant_id

    # Base query for calls in the period
    base = (
        db.query(Call)
        .filter(
            Call.tenant_id == tenant_id,
            Call.created_at >= date_from,
            Call.created_at <= date_to,
        )
    )

    total_calls = base.count()
    completed = base.filter(Call.status == CallStatus.completed)

    # ── Stats card data ───────────────────────────────────────────────

    # Calls today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    calls_today = (
        db.query(func.count(Call.id))
        .filter(Call.tenant_id == tenant_id, Call.created_at >= today_start)
        .scalar() or 0
    )
    calls_yesterday = (
        db.query(func.count(Call.id))
        .filter(
            Call.tenant_id == tenant_id,
            Call.created_at >= yesterday_start,
            Call.created_at < today_start,
        )
        .scalar() or 0
    )
    calls_today_change = (
        round(((calls_today - calls_yesterday) / calls_yesterday) * 100, 1)
        if calls_yesterday > 0 else 0
    )

    # Average quality score
    avg_score_result = completed.with_entities(
        func.avg(Call.overall_score)
    ).scalar()
    avg_quality_score = round(avg_score_result, 1) if avg_score_result else 0

    # Previous period for comparison
    period_length = (date_to - date_from).days
    prev_from = date_from - timedelta(days=period_length)
    prev_to = date_from

    prev_completed = (
        db.query(Call)
        .filter(
            Call.tenant_id == tenant_id,
            Call.created_at >= prev_from,
            Call.created_at < prev_to,
            Call.status == CallStatus.completed,
        )
    )
    prev_avg = prev_completed.with_entities(func.avg(Call.overall_score)).scalar()
    prev_avg_quality = round(prev_avg, 1) if prev_avg else 0
    avg_quality_change = round(avg_quality_score - prev_avg_quality, 1)

    # Hot leads count
    hot_count = completed.filter(
        Call.intent_classification == IntentClassification.hot
    ).count()
    prev_hot = prev_completed.filter(
        Call.intent_classification == IntentClassification.hot
    ).count()
    hot_leads_change = (
        round(((hot_count - prev_hot) / prev_hot) * 100, 1)
        if prev_hot > 0 else 0
    )

    # Team performance (% of calls scoring >= 70)
    good_calls = completed.filter(Call.overall_score >= 70).count()
    completed_count = completed.count()
    team_performance = round((good_calls / completed_count) * 100) if completed_count > 0 else 0

    prev_completed_count = prev_completed.count()
    prev_good = prev_completed.filter(Call.overall_score >= 70).count()
    prev_team_perf = round((prev_good / prev_completed_count) * 100) if prev_completed_count > 0 else 0
    team_performance_change = round(team_performance - prev_team_perf, 1)

    stats = DashboardStats(
        calls_today=calls_today,
        calls_today_change=calls_today_change,
        avg_quality_score=avg_quality_score,
        avg_quality_change=avg_quality_change,
        hot_leads_count=hot_count,
        hot_leads_change=hot_leads_change,
        team_performance=team_performance,
        team_performance_change=team_performance_change,
    )

    # ── Call trends (daily) ───────────────────────────────────────────

    calls_by_day_raw = (
        base.with_entities(
            func.date_trunc("day", Call.created_at).label("day"),
            func.count(Call.id).label("count"),
            func.avg(Call.overall_score).label("avg_score"),
        )
        .group_by("day")
        .order_by("day")
        .all()
    )
    call_trends = [
        CallTrend(
            date=row.day.strftime("%Y-%m-%d") if hasattr(row.day, "strftime") else str(row.day),
            count=row.count,
            avg_score=round(row.avg_score, 1) if row.avg_score else 0,
        )
        for row in calls_by_day_raw
    ]

    # ── Score distribution ────────────────────────────────────────────

    dist_map = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    score_rows = (
        completed.with_entities(Call.overall_score)
        .filter(Call.overall_score.isnot(None))
        .all()
    )
    for (score,) in score_rows:
        if score <= 20:
            dist_map["0-20"] += 1
        elif score <= 40:
            dist_map["21-40"] += 1
        elif score <= 60:
            dist_map["41-60"] += 1
        elif score <= 80:
            dist_map["61-80"] += 1
        else:
            dist_map["81-100"] += 1

    score_distribution = [
        ScoreDistribution(range=k, count=v) for k, v in dist_map.items()
    ]

    # ── Hot leads ─────────────────────────────────────────────────────

    hot_leads_raw = (
        completed
        .filter(Call.intent_classification == IntentClassification.hot)
        .outerjoin(User, Call.agent_id == User.id)
        .with_entities(
            Call.id,
            Call.lead_name,
            Call.lead_phone,
            Call.lead_intent_score,
            User.full_name.label("agent_name"),
            Call.created_at,
        )
        .order_by(Call.lead_intent_score.desc().nulls_last())
        .limit(10)
        .all()
    )
    hot_leads = [
        HotLeadItem(
            call_id=str(row.id),
            lead_name=row.lead_name or "",
            lead_phone=row.lead_phone or "",
            intent_score=row.lead_intent_score or 0,
            agent_name=row.agent_name or "",
            created_at=row.created_at.isoformat() if row.created_at else "",
        )
        for row in hot_leads_raw
    ]

    # ── Recent calls ──────────────────────────────────────────────────

    recent_raw = (
        base
        .outerjoin(User, Call.agent_id == User.id)
        .with_entities(
            Call.id,
            User.full_name.label("agent_name"),
            Call.agent_id,
            Call.lead_name,
            Call.lead_id,
            Call.lead_phone,
            Call.duration_seconds,
            Call.overall_score,
            Call.intent_classification,
            Call.lead_intent_score,
            Call.status,
            Call.source,
            Call.created_at,
        )
        .order_by(Call.created_at.desc())
        .limit(10)
        .all()
    )
    recent_calls = [
        CallListItemResponse(
            id=str(row.id),
            agent_name=row.agent_name or "",
            agent_id=str(row.agent_id) if row.agent_id else "",
            lead_name=row.lead_name or "",
            lead_id=row.lead_id or "",
            lead_phone=row.lead_phone or "",
            duration=row.duration_seconds or 0,
            overall_score=row.overall_score or 0,
            intent_classification=row.intent_classification.value if row.intent_classification else "cold",
            intent_score=row.lead_intent_score or 0,
            status=row.status.value if row.status else "uploaded",
            source=row.source or "",
            follow_up_urgency=None,
            created_at=row.created_at.isoformat() if row.created_at else "",
        )
        for row in recent_raw
    ]

    return TeamAnalytics(
        stats=stats,
        call_trends=call_trends,
        score_distribution=score_distribution,
        hot_leads=hot_leads,
        recent_calls=recent_calls,
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
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    date_from: Optional[datetime] = Query(default=None, description="Period start"),
    date_to: Optional[datetime] = Query(default=None, description="Period end"),
) -> AgentAnalytics:
    """Return detailed performance analytics for a specific agent."""
    set_tenant_context(db, current_user.tenant_id)

    date_from, date_to = _default_date_range(date_from, date_to)

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
    response_model=AnalyticsDataResponse,
    summary="Full analytics data for charts and insights",
)
def analytics_trends(
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    date_from: Optional[datetime] = Query(default=None, description="Period start"),
    date_to: Optional[datetime] = Query(default=None, description="Period end"),
) -> AnalyticsDataResponse:
    """Return comprehensive analytics matching the frontend AnalyticsData interface."""
    set_tenant_context(db, current_user.tenant_id)

    date_from, date_to = _default_date_range(date_from, date_to)
    tenant_id = current_user.tenant_id

    base = db.query(Call).filter(
        Call.tenant_id == tenant_id,
        Call.created_at >= date_from,
        Call.created_at <= date_to,
    )
    completed = base.filter(Call.status == CallStatus.completed)

    # ── Call volume (daily) ────────────────────────────────────────
    calls_by_day = (
        base.with_entities(
            func.date_trunc("day", Call.created_at).label("day"),
            func.count(Call.id).label("count"),
            func.avg(Call.overall_score).label("avg_score"),
        )
        .group_by("day")
        .order_by("day")
        .all()
    )
    call_volume = [
        CallTrend(
            date=row.day.strftime("%Y-%m-%d") if hasattr(row.day, "strftime") else str(row.day),
            count=row.count,
            avg_score=round(row.avg_score, 1) if row.avg_score else 0,
        )
        for row in calls_by_day
    ]

    # ── Quality trend (daily, completed only) ──────────────────────
    quality_by_day = (
        completed.with_entities(
            func.date_trunc("day", Call.created_at).label("day"),
            func.count(Call.id).label("count"),
            func.avg(Call.overall_score).label("avg_score"),
        )
        .filter(Call.overall_score.isnot(None))
        .group_by("day")
        .order_by("day")
        .all()
    )
    avg_quality_trend = [
        CallTrend(
            date=row.day.strftime("%Y-%m-%d") if hasattr(row.day, "strftime") else str(row.day),
            count=row.count,
            avg_score=round(row.avg_score, 1) if row.avg_score else 0,
        )
        for row in quality_by_day
    ]

    # ── Conversion funnel ──────────────────────────────────────────
    total_calls = base.count()
    completed_count = completed.count()
    warm_or_hot = completed.filter(
        Call.intent_classification.in_([IntentClassification.warm, IntentClassification.hot])
    ).count()
    hot_count = completed.filter(
        Call.intent_classification == IntentClassification.hot
    ).count()

    conversion_funnel = [
        ConversionFunnelStage(stage="Total Calls", count=total_calls),
        ConversionFunnelStage(stage="Completed", count=completed_count),
        ConversionFunnelStage(stage="Warm / Hot", count=warm_or_hot),
        ConversionFunnelStage(stage="Hot Leads", count=hot_count),
    ]

    # ── Lead classification breakdown ──────────────────────────────
    classification_rows = (
        completed.with_entities(
            Call.intent_classification,
            func.count(Call.id).label("cnt"),
        )
        .filter(Call.intent_classification.isnot(None))
        .group_by(Call.intent_classification)
        .all()
    )
    lead_classification = [
        LeadClassificationItem(
            classification=row.intent_classification.value
            if hasattr(row.intent_classification, "value")
            else str(row.intent_classification),
            count=row.cnt,
        )
        for row in classification_rows
    ]

    # ── Score distribution ─────────────────────────────────────────
    dist_map = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    score_rows = (
        completed.with_entities(Call.overall_score)
        .filter(Call.overall_score.isnot(None))
        .all()
    )
    for (score,) in score_rows:
        if score <= 20:
            dist_map["0-20"] += 1
        elif score <= 40:
            dist_map["21-40"] += 1
        elif score <= 60:
            dist_map["41-60"] += 1
        elif score <= 80:
            dist_map["61-80"] += 1
        else:
            dist_map["81-100"] += 1
    score_distribution = [
        ScoreDistribution(range=k, count=v) for k, v in dist_map.items()
    ]

    # ── Agent comparison ───────────────────────────────────────────
    agent_rows = (
        db.query(
            User.id.label("agent_id"),
            User.full_name.label("agent_name"),
            func.count(Call.id).label("total_calls"),
            func.avg(Call.overall_score).label("avg_quality"),
            func.avg(Call.lead_intent_score).label("avg_intent"),
            func.sum(
                case(
                    (Call.intent_classification == IntentClassification.hot, 1),
                    else_=0,
                )
            ).label("hot_leads_count"),
        )
        .join(Call, Call.agent_id == User.id)
        .filter(
            User.tenant_id == tenant_id,
            Call.tenant_id == tenant_id,
            Call.status == CallStatus.completed,
            Call.created_at >= date_from,
            Call.created_at <= date_to,
        )
        .group_by(User.id, User.full_name)
        .order_by(func.avg(Call.overall_score).desc().nulls_last())
        .all()
    )
    agent_comparison = [
        AgentComparisonItem(
            agent_id=str(row.agent_id),
            agent_name=row.agent_name,
            total_calls=row.total_calls,
            avg_quality_score=round(row.avg_quality, 1) if row.avg_quality else 0,
            avg_intent_score=round(row.avg_intent, 1) if row.avg_intent else 0,
            hot_leads_count=row.hot_leads_count or 0,
        )
        for row in agent_rows
    ]

    # ── Parameter trends (current vs previous period) ──────────────
    period_length = (date_to - date_from).days
    prev_from = date_from - timedelta(days=period_length)
    prev_to = date_from

    completed_ids = [c.id for c in completed.with_entities(Call.id).all()]
    prev_completed_ids = [
        c.id
        for c in db.query(Call.id)
        .filter(
            Call.tenant_id == tenant_id,
            Call.status == CallStatus.completed,
            Call.created_at >= prev_from,
            Call.created_at < prev_to,
        )
        .all()
    ]

    parameter_trends: list[ParameterTrend] = []
    if completed_ids:
        current_params = (
            db.query(
                QualityParameter.name.label("parameter_name"),
                func.avg(CallQualityScore.score).label("avg_score"),
            )
            .join(CallQualityScore, CallQualityScore.parameter_id == QualityParameter.id)
            .filter(
                CallQualityScore.call_id.in_(completed_ids),
                QualityParameter.tenant_id == tenant_id,
                QualityParameter.is_active.is_(True),
            )
            .group_by(QualityParameter.name)
            .all()
        )

        prev_param_map: dict[str, float] = {}
        if prev_completed_ids:
            prev_params = (
                db.query(
                    QualityParameter.name.label("parameter_name"),
                    func.avg(CallQualityScore.score).label("avg_score"),
                )
                .join(CallQualityScore, CallQualityScore.parameter_id == QualityParameter.id)
                .filter(
                    CallQualityScore.call_id.in_(prev_completed_ids),
                    QualityParameter.tenant_id == tenant_id,
                    QualityParameter.is_active.is_(True),
                )
                .group_by(QualityParameter.name)
                .all()
            )
            prev_param_map = {
                r.parameter_name: round(r.avg_score, 2) if r.avg_score else 0
                for r in prev_params
            }

        for row in current_params:
            current_avg = round(row.avg_score, 2) if row.avg_score else 0
            previous_avg = prev_param_map.get(row.parameter_name, 0)
            change = (
                round(((current_avg - previous_avg) / previous_avg) * 100, 1)
                if previous_avg > 0
                else 0
            )
            parameter_trends.append(
                ParameterTrend(
                    parameter_name=row.parameter_name,
                    current_avg=current_avg,
                    previous_avg=previous_avg,
                    change=change,
                )
            )

    return AnalyticsDataResponse(
        call_volume=call_volume,
        avg_quality_trend=avg_quality_trend,
        conversion_funnel=conversion_funnel,
        agent_comparison=agent_comparison,
        parameter_trends=parameter_trends,
        lead_classification=lead_classification,
        score_distribution=score_distribution,
    )


# ---------------------------------------------------------------------------
# GET /analytics/leaderboard
# ---------------------------------------------------------------------------


@router.get(
    "/leaderboard",
    response_model=List[LeaderboardEntry],
    summary="Agent leaderboard ranked by quality score",
)
def leaderboard(
    db: Annotated[Session, Depends(get_db_with_tenant)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    date_from: Optional[datetime] = Query(default=None, description="Period start"),
    date_to: Optional[datetime] = Query(default=None, description="Period end"),
    limit: int = Query(default=20, ge=1, le=100, description="Max entries to return"),
) -> List[LeaderboardEntry]:
    """Return a ranked leaderboard of agents ordered by average quality score."""
    set_tenant_context(db, current_user.tenant_id)

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
