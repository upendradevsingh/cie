"""Lead aggregation service — rolls up data from multiple calls per lead."""

import logging
from collections import Counter
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class LeadAggregator:
    """Aggregates call data into lead-level summaries.

    Usage::

        aggregator = LeadAggregator(db)
        await aggregator.update_lead(tenant_id, "lead-123")
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    async def update_lead(
        self,
        tenant_id: UUID,
        lead_id: str,
    ) -> None:
        """Aggregate all calls for a lead and update the Lead record.

        Creates the Lead record if it doesn't exist.
        """
        from app.models.call import Call, IntentClassification
        from app.models.lead import Lead

        logger.info("Aggregating lead data for tenant=%s lead=%s", tenant_id, lead_id)

        # Fetch all calls for this lead
        calls = (
            self._db.query(Call)
            .filter(
                Call.tenant_id == tenant_id,
                Call.lead_id == lead_id,
                Call.status == "completed",
            )
            .order_by(Call.created_at.desc())
            .all()
        )

        if not calls:
            logger.warning("No completed calls found for lead %s", lead_id)
            return

        # Get or create Lead record
        lead = (
            self._db.query(Lead)
            .filter(Lead.tenant_id == tenant_id, Lead.lead_id == lead_id)
            .first()
        )

        if lead is None:
            lead = Lead(tenant_id=tenant_id, lead_id=lead_id)
            self._db.add(lead)

        # Update basic info from latest call
        latest_call = calls[0]
        lead.lead_name = latest_call.lead_name or lead.lead_name
        lead.lead_phone = latest_call.lead_phone or lead.lead_phone
        lead.source = latest_call.source or lead.source

        # Aggregate scores
        lead.total_calls = len(calls)

        quality_scores = [c.overall_score for c in calls if c.overall_score is not None]
        lead.avg_quality_score = (
            sum(quality_scores) / len(quality_scores) if quality_scores else None
        )

        intent_scores = [
            c.lead_intent_score for c in calls if c.lead_intent_score is not None
        ]
        lead.avg_intent_score = (
            sum(intent_scores) / len(intent_scores) if intent_scores else None
        )

        # Latest classification
        if latest_call.intent_classification:
            lead.latest_intent_classification = (
                latest_call.intent_classification.value
                if hasattr(latest_call.intent_classification, "value")
                else str(latest_call.intent_classification)
            )

        # Date tracking
        lead.first_call_date = calls[-1].created_at
        lead.latest_call_date = calls[0].created_at

        # Quality trend
        if len(quality_scores) >= 2:
            first_half_avg = sum(quality_scores[: len(quality_scores) // 2]) / (
                len(quality_scores) // 2
            )
            second_half_avg = sum(quality_scores[len(quality_scores) // 2 :]) / (
                len(quality_scores) - len(quality_scores) // 2
            )
            if second_half_avg > first_half_avg + 5:
                lead.quality_trend = "improving"
            elif second_half_avg < first_half_avg - 5:
                lead.quality_trend = "declining"
            else:
                lead.quality_trend = "stable"

        # Aggregate insights
        all_objections: List[str] = []
        all_tags: List[str] = []
        all_pain_points: List[str] = []
        all_competitors: List[str] = []

        for call in calls:
            analysis = getattr(call, "analysis", None) or {}

            # Objections
            objections = analysis.get("key_objections", [])
            if isinstance(objections, list):
                for obj in objections:
                    if isinstance(obj, dict):
                        all_objections.append(obj.get("category", "Unknown"))

            # Tags
            tags = call.call_tags or []
            if isinstance(tags, list):
                all_tags.extend([str(t) for t in tags])

            # Pain points
            audit_keywords = call.sales_audit_keywords or {}
            if isinstance(audit_keywords, dict):
                pain_points = audit_keywords.get("customer_pain_points", [])
                if isinstance(pain_points, list):
                    for pp in pain_points:
                        if isinstance(pp, dict):
                            all_pain_points.append(pp.get("keyword", ""))

                # Competitors
                competitors = audit_keywords.get("competitor_mentions", [])
                if isinstance(competitors, list):
                    for comp in competitors:
                        if isinstance(comp, dict):
                            all_competitors.append(comp.get("keyword", ""))

        # Top objections (most frequent)
        objection_counts = Counter(all_objections)
        lead.top_objections = [obj for obj, _ in objection_counts.most_common(5)]

        # Unique tags
        lead.all_tags = list(set(all_tags))

        # Pain points (unique)
        lead.key_pain_points = list(set([p for p in all_pain_points if p]))

        # Competitors (unique)
        lead.competitors_mentioned = list(set([c for c in all_competitors if c]))

        # Latest BANT
        if latest_call.persona:
            from app.models.persona import CallPersona

            persona = (
                self._db.query(CallPersona)
                .filter(CallPersona.call_id == latest_call.id)
                .first()
            )
            if persona:
                lead.latest_budget_score = persona.budget_score
                lead.latest_authority_score = persona.authority_score
                lead.latest_need_score = persona.need_score
                lead.latest_timeline_score = persona.timeline_score
                lead.latest_persona_type = persona.persona_type

        # Action items count
        from app.models.action_item import ActionItem

        all_action_items = (
            self._db.query(ActionItem)
            .join(Call, ActionItem.call_id == Call.id)
            .filter(
                Call.tenant_id == tenant_id,
                Call.lead_id == lead_id,
            )
            .all()
        )

        lead.pending_action_items = sum(1 for ai in all_action_items if not ai.completed)
        lead.completed_action_items = sum(1 for ai in all_action_items if ai.completed)

        # Follow-up urgency (from latest call)
        latest_analysis = getattr(latest_call, "analysis", None) or {}
        lead.follow_up_urgency = latest_analysis.get("follow_up_urgency", "this_week")

        # Recommended next steps (from latest call)
        lead.recommended_next_steps = [
            {
                "description": latest_analysis.get("path_to_conversion", ""),
                "source": "AI-generated",
            }
        ]
        rebuttals = latest_analysis.get("rebuttals", [])
        if rebuttals:
            lead.recommended_next_steps.extend(
                [{"description": r, "source": "Rebuttal"} for r in rebuttals[:3]]
            )

        self._db.commit()
        self._db.refresh(lead)

        logger.info(
            "Lead aggregation complete for %s: %d calls, avg quality=%.1f",
            lead_id,
            lead.total_calls,
            lead.avg_quality_score or 0,
        )
