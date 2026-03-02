"""Correlation analysis service for quality parameters and intent signals.

Analyzes historical call data to identify which parameters and signals
correlate with successful outcomes (conversions, hot leads, high scores).
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ParameterCorrelation:
    """Correlation analysis for a single quality parameter."""

    parameter_name: str
    avg_score_hot_leads: float
    avg_score_cold_leads: float
    correlation_strength: float  # -1 to 1
    sample_size: int
    impact_category: str  # "high", "medium", "low", "negative"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "avg_score_hot_leads": round(self.avg_score_hot_leads, 2),
            "avg_score_cold_leads": round(self.avg_score_cold_leads, 2),
            "correlation_strength": round(self.correlation_strength, 3),
            "sample_size": self.sample_size,
            "impact_category": self.impact_category,
        }


@dataclass
class IntentSignalCorrelation:
    """Correlation analysis for a single intent signal."""

    signal_name: str
    detection_rate_hot: float  # % detected in hot leads
    detection_rate_cold: float  # % detected in cold leads
    correlation_strength: float
    sample_size: int
    impact_category: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "detection_rate_hot": round(self.detection_rate_hot, 2),
            "detection_rate_cold": round(self.detection_rate_cold, 2),
            "correlation_strength": round(self.correlation_strength, 3),
            "sample_size": self.sample_size,
            "impact_category": self.impact_category,
        }


@dataclass
class CorrelationAnalysis:
    """Complete correlation analysis results."""

    tenant_id: str
    period_days: int
    total_calls_analyzed: int
    hot_leads_count: int
    cold_leads_count: int

    # Top parameters that drive success
    top_parameters: List[ParameterCorrelation] = field(default_factory=list)

    # Parameters that negatively correlate
    negative_parameters: List[ParameterCorrelation] = field(default_factory=list)

    # Intent signals analysis
    top_signals: List[IntentSignalCorrelation] = field(default_factory=list)

    # Recommended actions
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": {
                "tenant_id": self.tenant_id,
                "period_days": self.period_days,
                "total_calls_analyzed": self.total_calls_analyzed,
                "hot_leads_count": self.hot_leads_count,
                "cold_leads_count": self.cold_leads_count,
            },
            "parameter_correlations": {
                "top_drivers": [p.to_dict() for p in self.top_parameters],
                "negative_indicators": [p.to_dict() for p in self.negative_parameters],
            },
            "intent_signal_correlations": [s.to_dict() for s in self.top_signals],
            "recommendations": self.recommendations,
        }


# ---------------------------------------------------------------------------
# Correlation analyzer
# ---------------------------------------------------------------------------


class CorrelationAnalyzer:
    """Analyzes correlations between call metrics and outcomes.

    Usage::

        analyzer = CorrelationAnalyzer(db)
        results = await analyzer.analyze(tenant_id, period_days=30)
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    async def analyze(
        self,
        tenant_id: UUID,
        period_days: int = 30,
        min_sample_size: int = 10,
    ) -> Dict[str, Any]:
        """Perform correlation analysis for the specified period.

        Parameters
        ----------
        tenant_id:
            Tenant to analyze
        period_days:
            Number of days of historical data to analyze
        min_sample_size:
            Minimum number of calls required for meaningful correlation

        Returns
        -------
        dict
            Serialized CorrelationAnalysis with insights
        """
        from datetime import datetime, timedelta, timezone

        from app.models.call import Call, IntentClassification

        logger.info(
            "Starting correlation analysis for tenant=%s period=%d days",
            tenant_id,
            period_days,
        )

        # Fetch completed calls from the period
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)

        calls = (
            self._db.query(Call)
            .filter(
                and_(
                    Call.tenant_id == tenant_id,
                    Call.status == "completed",
                    Call.created_at >= cutoff_date,
                    Call.overall_score.isnot(None),
                    Call.intent_classification.isnot(None),
                )
            )
            .all()
        )

        if len(calls) < min_sample_size:
            logger.warning(
                "Insufficient data for correlation analysis: %d calls (min: %d)",
                len(calls),
                min_sample_size,
            )
            return self._empty_analysis(tenant_id, period_days, len(calls))

        # Segment calls by intent
        hot_calls = [
            c
            for c in calls
            if c.intent_classification == IntentClassification.hot
        ]
        cold_calls = [
            c
            for c in calls
            if c.intent_classification == IntentClassification.cold
        ]

        analysis = CorrelationAnalysis(
            tenant_id=str(tenant_id),
            period_days=period_days,
            total_calls_analyzed=len(calls),
            hot_leads_count=len(hot_calls),
            cold_leads_count=len(cold_calls),
        )

        # Analyze quality parameters
        param_correlations = self._analyze_parameters(hot_calls, cold_calls)
        analysis.top_parameters = [
            p for p in param_correlations if p.correlation_strength > 0
        ]
        analysis.top_parameters.sort(
            key=lambda p: p.correlation_strength, reverse=True
        )
        analysis.top_parameters = analysis.top_parameters[:10]

        analysis.negative_parameters = [
            p for p in param_correlations if p.correlation_strength < 0
        ]
        analysis.negative_parameters.sort(key=lambda p: p.correlation_strength)
        analysis.negative_parameters = analysis.negative_parameters[:5]

        # Analyze intent signals
        signal_correlations = self._analyze_signals(hot_calls, cold_calls)
        analysis.top_signals = signal_correlations
        analysis.top_signals.sort(
            key=lambda s: s.correlation_strength, reverse=True
        )
        analysis.top_signals = analysis.top_signals[:10]

        # Generate recommendations
        analysis.recommendations = self._generate_recommendations(analysis)

        logger.info(
            "Correlation analysis complete: %d param correlations, %d signal correlations",
            len(param_correlations),
            len(signal_correlations),
        )

        return analysis.to_dict()

    def _analyze_parameters(
        self,
        hot_calls: List,
        cold_calls: List,
    ) -> List[ParameterCorrelation]:
        """Compute correlation for each quality parameter."""
        # Collect scores by parameter
        param_scores_hot: Dict[str, List[float]] = {}
        param_scores_cold: Dict[str, List[float]] = {}

        for call in hot_calls:
            analysis = getattr(call, "analysis", None) or {}
            for qs in analysis.get("quality_scores", []):
                name = qs.get("parameter_name", "Unknown")
                score = qs.get("score")
                if score is not None:
                    param_scores_hot.setdefault(name, []).append(float(score))

        for call in cold_calls:
            analysis = getattr(call, "analysis", None) or {}
            for qs in analysis.get("quality_scores", []):
                name = qs.get("parameter_name", "Unknown")
                score = qs.get("score")
                if score is not None:
                    param_scores_cold.setdefault(name, []).append(float(score))

        # Compute correlations
        correlations: List[ParameterCorrelation] = []

        all_params = set(param_scores_hot.keys()) | set(param_scores_cold.keys())

        for param in all_params:
            hot_scores = param_scores_hot.get(param, [])
            cold_scores = param_scores_cold.get(param, [])

            if not hot_scores or not cold_scores:
                continue  # Need both to compare

            avg_hot = sum(hot_scores) / len(hot_scores)
            avg_cold = sum(cold_scores) / len(cold_scores)

            # Simple correlation: difference normalized by total range
            # Positive = higher in hot leads (good)
            # Negative = higher in cold leads (bad)
            diff = avg_hot - avg_cold
            correlation = diff / 10.0  # Normalize to -1..1 range (scores are 0-10)

            # Categorize impact
            if abs(correlation) >= 0.3:
                impact = "high"
            elif abs(correlation) >= 0.15:
                impact = "medium"
            elif correlation < 0:
                impact = "negative"
            else:
                impact = "low"

            correlations.append(
                ParameterCorrelation(
                    parameter_name=param,
                    avg_score_hot_leads=avg_hot,
                    avg_score_cold_leads=avg_cold,
                    correlation_strength=correlation,
                    sample_size=len(hot_scores) + len(cold_scores),
                    impact_category=impact,
                )
            )

        return correlations

    def _analyze_signals(
        self,
        hot_calls: List,
        cold_calls: List,
    ) -> List[IntentSignalCorrelation]:
        """Compute correlation for each intent signal."""
        # Count signal detections
        signal_counts_hot: Dict[str, int] = {}
        signal_counts_cold: Dict[str, int] = {}

        for call in hot_calls:
            analysis = getattr(call, "analysis", None) or {}
            for sig in analysis.get("intent_signals", []):
                name = sig.get("signal_name", "Unknown")
                detected = sig.get("detected", False)
                if detected:
                    signal_counts_hot[name] = signal_counts_hot.get(name, 0) + 1

        for call in cold_calls:
            analysis = getattr(call, "analysis", None) or {}
            for sig in analysis.get("intent_signals", []):
                name = sig.get("signal_name", "Unknown")
                detected = sig.get("detected", False)
                if detected:
                    signal_counts_cold[name] = signal_counts_cold.get(name, 0) + 1

        # Compute correlations
        correlations: List[IntentSignalCorrelation] = []

        all_signals = set(signal_counts_hot.keys()) | set(signal_counts_cold.keys())

        for signal in all_signals:
            count_hot = signal_counts_hot.get(signal, 0)
            count_cold = signal_counts_cold.get(signal, 0)

            rate_hot = (count_hot / len(hot_calls) * 100) if hot_calls else 0
            rate_cold = (count_cold / len(cold_calls) * 100) if cold_calls else 0

            # Correlation: higher detection in hot = positive
            diff = rate_hot - rate_cold
            correlation = diff / 100.0  # Normalize to -1..1

            # Categorize
            if abs(correlation) >= 0.3:
                impact = "high"
            elif abs(correlation) >= 0.15:
                impact = "medium"
            elif correlation < 0:
                impact = "negative"
            else:
                impact = "low"

            correlations.append(
                IntentSignalCorrelation(
                    signal_name=signal,
                    detection_rate_hot=rate_hot,
                    detection_rate_cold=rate_cold,
                    correlation_strength=correlation,
                    sample_size=count_hot + count_cold,
                    impact_category=impact,
                )
            )

        return correlations

    def _generate_recommendations(
        self,
        analysis: CorrelationAnalysis,
    ) -> List[str]:
        """Generate actionable recommendations based on correlations."""
        recs: List[str] = []

        # Top parameters
        if analysis.top_parameters:
            top_param = analysis.top_parameters[0]
            recs.append(
                f"Focus coaching on '{top_param.parameter_name}' — it shows the "
                f"strongest correlation with hot leads "
                f"(+{top_param.correlation_strength:.2f} correlation)."
            )

        # Negative parameters
        if analysis.negative_parameters:
            neg_param = analysis.negative_parameters[0]
            recs.append(
                f"Address '{neg_param.parameter_name}' immediately — it's "
                f"negatively correlated with success "
                f"({neg_param.correlation_strength:.2f} correlation)."
            )

        # Top signals
        if analysis.top_signals:
            top_signal = analysis.top_signals[0]
            recs.append(
                f"Train agents to elicit '{top_signal.signal_name}' — it appears "
                f"{top_signal.detection_rate_hot:.1f}% of the time in hot leads "
                f"vs {top_signal.detection_rate_cold:.1f}% in cold leads."
            )

        # Sample size warning
        if analysis.total_calls_analyzed < 50:
            recs.append(
                "Note: Correlation analysis is based on limited data. "
                "Results will be more reliable with 50+ calls."
            )

        if not recs:
            recs.append("Insufficient data for specific recommendations.")

        return recs

    @staticmethod
    def _empty_analysis(
        tenant_id: UUID,
        period_days: int,
        total_calls: int,
    ) -> Dict[str, Any]:
        """Return an empty analysis structure when there's insufficient data."""
        return {
            "metadata": {
                "tenant_id": str(tenant_id),
                "period_days": period_days,
                "total_calls_analyzed": total_calls,
                "hot_leads_count": 0,
                "cold_leads_count": 0,
            },
            "parameter_correlations": {
                "top_drivers": [],
                "negative_indicators": [],
            },
            "intent_signal_correlations": [],
            "recommendations": [
                "Insufficient data for correlation analysis. "
                f"Only {total_calls} calls found in the last {period_days} days. "
                "Minimum 10 completed calls required."
            ],
        }
