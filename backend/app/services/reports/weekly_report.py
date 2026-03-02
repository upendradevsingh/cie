"""Weekly report generation service.

Aggregates call data for a given tenant over a week period, computing
per-agent and team-level statistics, quality score trends, lead intelligence
summaries, and top-performing highlights.

The generator supports two modes of operation:

1. **Structured models** — when the full model suite (``Call``,
   ``QualityParameter``, ``CallQualityScore``, ``ActionItem``) is
   available, it queries each table directly for precise aggregation.
2. **JSON-based fallback** — when lightweight models store analysis
   results as a JSON column (``Call.analysis_result``), the generator
   extracts scores from the JSON payload.

Both paths produce an identical report schema.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AgentStats:
    """Performance statistics for a single agent over the reporting period."""

    agent_id: str
    agent_name: str
    total_calls: int = 0
    avg_quality_score: float = 0.0
    avg_intent_score: float = 0.0
    hot_leads: int = 0
    warm_leads: int = 0
    cold_leads: int = 0
    completed_action_items: int = 0
    pending_action_items: int = 0
    top_parameter_scores: Dict[str, float] = field(default_factory=dict)
    bottom_parameter_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "total_calls": self.total_calls,
            "avg_quality_score": round(self.avg_quality_score, 2),
            "avg_intent_score": round(self.avg_intent_score, 2),
            "hot_leads": self.hot_leads,
            "warm_leads": self.warm_leads,
            "cold_leads": self.cold_leads,
            "completed_action_items": self.completed_action_items,
            "pending_action_items": self.pending_action_items,
            "top_parameter_scores": {
                k: round(v, 2) for k, v in self.top_parameter_scores.items()
            },
            "bottom_parameter_scores": {
                k: round(v, 2) for k, v in self.bottom_parameter_scores.items()
            },
        }


@dataclass
class WeeklyReportData:
    """Complete data payload for a weekly performance report."""

    tenant_id: str
    week_start: str
    week_end: str
    generated_at: str

    # Team-level summary
    total_calls: int = 0
    completed_calls: int = 0
    failed_calls: int = 0
    total_duration_minutes: float = 0.0
    avg_duration_minutes: float = 0.0
    avg_quality_score: float = 0.0
    avg_intent_score: float = 0.0
    hot_leads: int = 0
    warm_leads: int = 0
    cold_leads: int = 0

    # Per-agent breakdowns
    agent_stats: List[Dict[str, Any]] = field(default_factory=list)

    # Quality parameter averages
    parameter_averages: Dict[str, float] = field(default_factory=dict)

    # Top calls
    top_calls: List[Dict[str, Any]] = field(default_factory=list)

    # Improvement areas
    areas_for_improvement: List[Dict[str, Any]] = field(default_factory=list)

    # Hot leads
    hot_leads_details: List[Dict[str, Any]] = field(default_factory=list)

    # Week-over-week trends
    trends: Dict[str, Any] = field(default_factory=dict)

    # Highlights
    top_agent_quality: Optional[Dict[str, Any]] = None
    top_agent_leads: Optional[Dict[str, Any]] = None
    most_improved_agent: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary for JSON storage."""
        return {
            "metadata": {
                "tenant_id": self.tenant_id,
                "week_start": self.week_start,
                "week_end": self.week_end,
                "generated_at": self.generated_at,
            },
            "summary": {
                "total_calls": self.total_calls,
                "completed_calls": self.completed_calls,
                "failed_calls": self.failed_calls,
                "total_duration_minutes": round(self.total_duration_minutes, 1),
                "avg_duration_minutes": round(self.avg_duration_minutes, 1),
                "avg_quality_score": round(self.avg_quality_score, 2),
                "avg_intent_score": round(self.avg_intent_score, 2),
                "hot_leads_count": self.hot_leads,
                "warm_leads_count": self.warm_leads,
                "cold_leads_count": self.cold_leads,
            },
            "agent_performance": self.agent_stats,
            "parameter_averages": {
                k: round(v, 2) for k, v in self.parameter_averages.items()
            },
            "top_calls": self.top_calls,
            "areas_for_improvement": self.areas_for_improvement,
            "hot_leads": self.hot_leads_details,
            "trends": self.trends,
            "highlights": {
                "top_agent_quality": self.top_agent_quality,
                "top_agent_leads": self.top_agent_leads,
                "most_improved_agent": self.most_improved_agent,
            },
        }


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class WeeklyReportGenerator:
    """Generate weekly performance reports for a tenant.

    Usage::

        generator = WeeklyReportGenerator(db)
        report_data = await generator.generate(
            tenant_id=UUID("..."),
            week_start=date(2026, 2, 24),
            week_end=date(2026, 3, 2),
        )

    Parameters
    ----------
    db:
        An active SQLAlchemy session.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    async def generate(
        self,
        tenant_id: uuid.UUID,
        week_start: date,
        week_end: date,
    ) -> Dict[str, Any]:
        """Generate a full weekly report and return it as a dictionary.

        Parameters
        ----------
        tenant_id:
            The tenant to generate the report for.
        week_start:
            Start of the reporting week (inclusive).
        week_end:
            End of the reporting week (inclusive).

        Returns
        -------
        dict
            Serialised :class:`WeeklyReportData` containing:

            * ``metadata`` — report period and generation timestamp
            * ``summary`` — overall statistics for the week
            * ``agent_performance`` — per-agent breakdown
            * ``top_calls`` — highest-scored calls
            * ``areas_for_improvement`` — lowest scoring quality parameters
            * ``hot_leads`` — leads classified as "hot"
            * ``trends`` — comparison with the previous week
            * ``highlights`` — top agent recognitions
        """
        # Attempt to import required models.
        try:
            from app.models.call import Call, CallStatus, IntentClassification
        except ImportError:
            logger.warning(
                "Call model not yet available — returning empty report scaffold"
            )
            return self._empty_report(tenant_id, week_start, week_end)

        logger.info(
            "Generating weekly report for tenant=%s week=%s to %s",
            tenant_id,
            week_start,
            week_end,
        )

        report = WeeklyReportData(
            tenant_id=str(tenant_id),
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        # --- Fetch current and previous week calls ---
        calls = self._fetch_calls(tenant_id, week_start, week_end)
        if not calls:
            logger.info("No calls found for the reporting period.")
            return report.to_dict()

        prev_start = week_start - timedelta(days=7)
        prev_end = week_end - timedelta(days=7)
        prev_calls = self._fetch_calls(tenant_id, prev_start, prev_end)

        # Determine which model shape we have.
        has_status_enum = hasattr(calls[0], "status") and hasattr(
            calls[0].status, "value" if hasattr(calls[0].status, "value") else ""
        )

        # --- Team-level aggregates ---
        report.total_calls = len(calls)

        # Classify completed/failed using status attribute or string comparison.
        completed_calls: list = []
        for c in calls:
            status_val = (
                c.status.value if hasattr(c.status, "value") else str(c.status)
            )
            if status_val == "completed":
                completed_calls.append(c)
            elif status_val == "failed":
                report.failed_calls += 1

        report.completed_calls = len(completed_calls)

        # Duration
        durations = [
            (getattr(c, "duration_seconds", 0) or 0) / 60.0
            for c in completed_calls
        ]
        report.total_duration_minutes = sum(durations)
        report.avg_duration_minutes = (
            report.total_duration_minutes / len(completed_calls)
            if completed_calls
            else 0.0
        )

        # Scores — try direct columns first, then fall back to JSON analysis.
        quality_scores: List[float] = []
        intent_scores: List[float] = []

        for c in completed_calls:
            qs = self._get_quality_score(c)
            if qs is not None:
                quality_scores.append(qs)
            isc = self._get_intent_score(c)
            if isc is not None:
                intent_scores.append(isc)

            classification = self._get_intent_classification(c)
            if classification == "hot":
                report.hot_leads += 1
            elif classification == "warm":
                report.warm_leads += 1
            else:
                report.cold_leads += 1

        report.avg_quality_score = (
            sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        )
        report.avg_intent_score = (
            sum(intent_scores) / len(intent_scores) if intent_scores else 0.0
        )

        # --- Per-agent stats ---
        agent_call_map: Dict[uuid.UUID, list] = {}
        for call in completed_calls:
            agent_id = getattr(call, "agent_id", None)
            if agent_id:
                agent_call_map.setdefault(agent_id, []).append(call)

        agent_stats_list: List[AgentStats] = []
        for agent_id, agent_calls in agent_call_map.items():
            stats = self._compute_agent_stats(agent_id, agent_calls)
            agent_stats_list.append(stats)

        agent_stats_list.sort(key=lambda s: s.avg_quality_score, reverse=True)
        report.agent_stats = [s.to_dict() for s in agent_stats_list]

        # --- Quality parameter averages ---
        report.parameter_averages = self._compute_parameter_averages(
            completed_calls
        )

        # --- Top calls ---
        report.top_calls = self._build_top_calls(completed_calls, limit=10)

        # --- Areas for improvement ---
        report.areas_for_improvement = self._build_improvement_areas(completed_calls)

        # --- Hot leads details ---
        report.hot_leads_details = self._build_hot_leads(completed_calls)

        # --- Trends (vs. previous week) ---
        report.trends = self._build_trends(report, prev_calls)

        # --- Highlights ---
        if agent_stats_list:
            best_quality = max(agent_stats_list, key=lambda s: s.avg_quality_score)
            report.top_agent_quality = {
                "agent_id": best_quality.agent_id,
                "agent_name": best_quality.agent_name,
                "avg_quality_score": round(best_quality.avg_quality_score, 2),
            }

            best_leads = max(agent_stats_list, key=lambda s: s.hot_leads)
            report.top_agent_leads = {
                "agent_id": best_leads.agent_id,
                "agent_name": best_leads.agent_name,
                "hot_leads": best_leads.hot_leads,
            }

        return report.to_dict()

    # ------------------------------------------------------------------
    # Data access helpers
    # ------------------------------------------------------------------

    def _fetch_calls(
        self,
        tenant_id: uuid.UUID,
        start: date,
        end: date,
    ) -> list:
        """Fetch all calls for the tenant in the given date range."""
        from app.models.call import Call

        return (
            self._db.query(Call)
            .options(joinedload(Call.agent))
            .filter(
                and_(
                    Call.tenant_id == tenant_id,
                    func.date(Call.created_at) >= start,
                    func.date(Call.created_at) <= end,
                )
            )
            .all()
        )

    @staticmethod
    def _get_quality_score(call: Any) -> Optional[float]:
        """Extract the overall quality score from a call."""
        # Direct column
        if hasattr(call, "overall_score") and call.overall_score is not None:
            return float(call.overall_score)
        # JSON analysis result
        analysis = getattr(call, "analysis_result", None)
        if isinstance(analysis, dict):
            val = analysis.get("overall_score")
            if val is not None:
                return float(val)
        return None

    @staticmethod
    def _get_intent_score(call: Any) -> Optional[float]:
        """Extract the lead intent score from a call."""
        if hasattr(call, "lead_intent_score") and call.lead_intent_score is not None:
            return float(call.lead_intent_score)
        analysis = getattr(call, "analysis_result", None)
        if isinstance(analysis, dict):
            val = analysis.get("lead_intent_score")
            if val is not None:
                return float(val)
        return None

    @staticmethod
    def _get_intent_classification(call: Any) -> str:
        """Extract the intent classification string from a call."""
        if hasattr(call, "intent_classification"):
            ic = call.intent_classification
            if ic is not None:
                return ic.value if hasattr(ic, "value") else str(ic).lower()
        analysis = getattr(call, "analysis_result", None)
        if isinstance(analysis, dict):
            return analysis.get("intent_classification", "cold").lower()
        return "cold"

    def _compute_agent_stats(
        self,
        agent_id: uuid.UUID,
        agent_calls: list,
    ) -> AgentStats:
        """Compute statistics for a single agent."""
        from app.models.user import User

        agent: Optional[User] = (
            self._db.query(User).filter(User.id == agent_id).first()
        )
        agent_name = agent.full_name if agent else "Unknown Agent"

        stats = AgentStats(
            agent_id=str(agent_id),
            agent_name=agent_name,
            total_calls=len(agent_calls),
        )

        scores = [
            s for s in (self._get_quality_score(c) for c in agent_calls) if s is not None
        ]
        intent_scores = [
            s for s in (self._get_intent_score(c) for c in agent_calls) if s is not None
        ]

        stats.avg_quality_score = sum(scores) / len(scores) if scores else 0.0
        stats.avg_intent_score = (
            sum(intent_scores) / len(intent_scores) if intent_scores else 0.0
        )

        for c in agent_calls:
            classification = self._get_intent_classification(c)
            if classification == "hot":
                stats.hot_leads += 1
            elif classification == "warm":
                stats.warm_leads += 1
            else:
                stats.cold_leads += 1

        # Count action items if the model is available.
        try:
            from app.models.action_item import ActionItem

            call_ids = [c.id for c in agent_calls]
            if call_ids:
                stats.completed_action_items = (
                    self._db.query(ActionItem)
                    .filter(
                        and_(
                            ActionItem.call_id.in_(call_ids),
                            ActionItem.completed.is_(True),
                        )
                    )
                    .count()
                )
                stats.pending_action_items = (
                    self._db.query(ActionItem)
                    .filter(
                        and_(
                            ActionItem.call_id.in_(call_ids),
                            ActionItem.completed.is_(False),
                        )
                    )
                    .count()
                )
        except (ImportError, Exception):
            # ActionItem model not available — count from JSON analysis.
            for c in agent_calls:
                analysis = getattr(c, "analysis_result", None)
                if isinstance(analysis, dict):
                    stats.pending_action_items += len(
                        analysis.get("action_items", [])
                    )

        # Per-parameter scores for the agent (top/bottom).
        param_scores: Dict[str, List[float]] = {}
        for c in agent_calls:
            analysis = getattr(c, "analysis_result", None)
            if isinstance(analysis, dict):
                for qs in analysis.get("quality_scores", []):
                    name = qs.get("parameter_name", "Unknown")
                    score = qs.get("score")
                    if score is not None:
                        param_scores.setdefault(name, []).append(float(score))

        if param_scores:
            averages = {
                k: sum(v) / len(v) for k, v in param_scores.items()
            }
            sorted_params = sorted(averages.items(), key=lambda x: x[1])
            stats.bottom_parameter_scores = dict(sorted_params[:3])
            stats.top_parameter_scores = dict(sorted_params[-3:])

        return stats

    @staticmethod
    def _compute_parameter_averages(completed_calls: list) -> Dict[str, float]:
        """Compute average score per quality parameter across all calls.

        First attempts to use the ``CallQualityScore`` model for a proper
        SQL aggregation.  Falls back to extracting scores from the JSON
        ``analysis_result`` column.
        """
        param_scores: Dict[str, List[float]] = {}

        for c in completed_calls:
            analysis = getattr(c, "analysis_result", None)
            if isinstance(analysis, dict):
                for qs in analysis.get("quality_scores", []):
                    name = qs.get("parameter_name", "Unknown")
                    score = qs.get("score")
                    if score is not None:
                        param_scores.setdefault(name, []).append(float(score))

        return {
            k: sum(v) / len(v) for k, v in param_scores.items()
        }

    @staticmethod
    def _build_top_calls(calls: list, limit: int = 10) -> List[Dict[str, Any]]:
        """Return the highest-scored calls for the week."""
        scored: List[Tuple[float, Any]] = []

        for call in calls:
            score = WeeklyReportGenerator._get_quality_score(call)
            if score is not None:
                scored.append((score, call))

        scored.sort(key=lambda x: x[0], reverse=True)

        result: List[Dict[str, Any]] = []
        for score, call in scored[:limit]:
            agent = getattr(call, "agent", None)
            agent_name = agent.full_name if agent else "Unknown"
            result.append(
                {
                    "call_id": str(call.id),
                    "agent_name": agent_name,
                    "lead_name": getattr(call, "lead_name", None) or "Unknown",
                    "overall_score": round(score, 2),
                    "intent_classification": (
                        WeeklyReportGenerator._get_intent_classification(call)
                    ),
                    "duration_minutes": round(
                        (getattr(call, "duration_seconds", 0) or 0) / 60.0, 1
                    ),
                    "created_at": (
                        call.created_at.isoformat() if call.created_at else None
                    ),
                }
            )

        return result

    @staticmethod
    def _build_improvement_areas(calls: list) -> List[Dict[str, Any]]:
        """Identify the quality parameters with the lowest average scores."""
        param_scores: Dict[str, List[float]] = {}

        for call in calls:
            analysis = getattr(call, "analysis_result", None)
            if not isinstance(analysis, dict):
                continue
            for qs in analysis.get("quality_scores", []):
                name = qs.get("parameter_name", "Unknown")
                score = qs.get("score")
                if score is not None:
                    param_scores.setdefault(name, []).append(float(score))

        averages: List[Dict[str, Any]] = []
        for name, scores in param_scores.items():
            avg = sum(scores) / len(scores) if scores else 0.0
            averages.append(
                {
                    "parameter_name": name,
                    "avg_score": round(avg, 2),
                    "sample_size": len(scores),
                }
            )

        averages.sort(key=lambda x: x["avg_score"])
        return averages[:5]

    @staticmethod
    def _build_hot_leads(calls: list) -> List[Dict[str, Any]]:
        """Extract all calls classified as "hot" leads."""
        hot: List[Dict[str, Any]] = []

        for call in calls:
            classification = WeeklyReportGenerator._get_intent_classification(call)
            if classification != "hot":
                continue

            analysis = getattr(call, "analysis_result", None)
            intent_score = WeeklyReportGenerator._get_intent_score(call) or 0

            agent = getattr(call, "agent", None)
            agent_name = agent.full_name if agent else "Unknown"
            hot.append(
                {
                    "call_id": str(call.id),
                    "lead_name": getattr(call, "lead_name", None) or "Unknown",
                    "lead_phone": getattr(call, "lead_phone", None),
                    "agent_name": agent_name,
                    "intent_score": round(intent_score, 1),
                    "follow_up_urgency": (
                        analysis.get("follow_up_urgency", "this_week")
                        if isinstance(analysis, dict)
                        else "this_week"
                    ),
                    "path_to_conversion": (
                        analysis.get("path_to_conversion", "")
                        if isinstance(analysis, dict)
                        else ""
                    ),
                    "created_at": (
                        call.created_at.isoformat() if call.created_at else None
                    ),
                }
            )

        hot.sort(key=lambda x: x["intent_score"], reverse=True)
        return hot

    def _build_trends(
        self,
        current_report: WeeklyReportData,
        prev_calls: list,
    ) -> Dict[str, Any]:
        """Compare the current week with the previous week."""
        # Build summary for previous week.
        prev_quality: List[float] = []
        prev_intent: List[float] = []
        prev_hot = prev_warm = prev_cold = 0
        prev_completed = 0
        prev_durations: List[float] = []

        for c in prev_calls:
            status_val = (
                c.status.value if hasattr(c.status, "value") else str(c.status)
            )
            if status_val != "completed":
                continue
            prev_completed += 1
            prev_durations.append((getattr(c, "duration_seconds", 0) or 0) / 60.0)

            qs = self._get_quality_score(c)
            if qs is not None:
                prev_quality.append(qs)
            isc = self._get_intent_score(c)
            if isc is not None:
                prev_intent.append(isc)
            classification = self._get_intent_classification(c)
            if classification == "hot":
                prev_hot += 1
            elif classification == "warm":
                prev_warm += 1
            else:
                prev_cold += 1

        prev_avg_quality = (
            sum(prev_quality) / len(prev_quality) if prev_quality else 0.0
        )
        prev_avg_intent = (
            sum(prev_intent) / len(prev_intent) if prev_intent else 0.0
        )
        prev_avg_duration = (
            sum(prev_durations) / prev_completed if prev_completed else 0.0
        )

        def _delta(current_val: float, prev_val: float) -> Dict[str, Any]:
            diff = current_val - prev_val
            pct = (diff / prev_val * 100) if prev_val else 0.0
            return {
                "current": round(current_val, 2),
                "previous": round(prev_val, 2),
                "change": round(diff, 2),
                "change_pct": round(pct, 1),
            }

        return {
            "total_calls": _delta(
                float(current_report.completed_calls),
                float(prev_completed),
            ),
            "avg_quality_score": _delta(
                current_report.avg_quality_score,
                prev_avg_quality,
            ),
            "avg_intent_score": _delta(
                current_report.avg_intent_score,
                prev_avg_intent,
            ),
            "hot_leads_count": _delta(
                float(current_report.hot_leads),
                float(prev_hot),
            ),
            "avg_duration_minutes": _delta(
                current_report.avg_duration_minutes,
                prev_avg_duration,
            ),
        }

    @staticmethod
    def _empty_report(
        tenant_id: uuid.UUID,
        week_start: date,
        week_end: date,
    ) -> Dict[str, Any]:
        """Return a report scaffold when no data or models are available."""
        return {
            "metadata": {
                "tenant_id": str(tenant_id),
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "note": "Call model not available — report is empty.",
            },
            "summary": {
                "total_calls": 0,
                "completed_calls": 0,
                "failed_calls": 0,
                "total_duration_minutes": 0.0,
                "avg_duration_minutes": 0.0,
                "avg_quality_score": 0.0,
                "avg_intent_score": 0.0,
                "hot_leads_count": 0,
                "warm_leads_count": 0,
                "cold_leads_count": 0,
            },
            "agent_performance": [],
            "parameter_averages": {},
            "top_calls": [],
            "areas_for_improvement": [],
            "hot_leads": [],
            "trends": {},
            "highlights": {
                "top_agent_quality": None,
                "top_agent_leads": None,
                "most_improved_agent": None,
            },
        }
