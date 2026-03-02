"""LLM-powered call analysis service.

Sends a sales call transcript along with tenant-configurable evaluation
criteria to an LLM and parses the structured JSON response into an
:class:`AnalysisResult`.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template loading
# ---------------------------------------------------------------------------

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


def _load_template(template_name: str = "call_analysis.jinja2") -> str:
    """Load and return a Jinja2 template from the prompts directory.

    Parameters
    ----------
    template_name:
        Name of the template file inside ``app/prompts/``.

    Returns
    -------
    str
        The raw template string.
    """
    env = Environment(
        loader=FileSystemLoader(str(_PROMPTS_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    try:
        template = env.get_template(template_name)
    except TemplateNotFound:
        raise FileNotFoundError(
            f"Prompt template '{template_name}' not found in {_PROMPTS_DIR}"
        )
    return template


# ---------------------------------------------------------------------------
# Data classes for structured analysis output
# ---------------------------------------------------------------------------


@dataclass
class QualityScore:
    """Score for a single quality evaluation parameter."""

    parameter_name: str
    score: float
    justification: str


@dataclass
class IntentSignalResult:
    """Detection result for a single intent signal."""

    signal_name: str
    detected: bool
    details: str


@dataclass
class ActionItem:
    """An action item extracted from the call."""

    description: str
    category: str
    urgency: str


@dataclass
class PersonaResult:
    """BANT-based persona classification."""

    type: str
    budget_score: float
    authority_score: float
    need_score: float
    timeline_score: float
    discovery_insights: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Complete structured output from the call analysis pipeline.

    This object encapsulates every dimension of the analysis: quality
    scoring, lead intelligence, persona identification, and action items.
    """

    quality_scores: List[QualityScore]
    overall_score: float
    lead_intent_score: float
    intent_classification: str  # "hot", "warm", or "cold"
    intent_signals: List[IntentSignalResult]
    persona: PersonaResult
    action_items: List[ActionItem]
    path_to_conversion: str
    rebuttals: List[str]
    key_data_points: Dict[str, Any]
    follow_up_urgency: str
    call_summary: str
    escalation_keywords: List[Dict[str, str]] = field(default_factory=list)
    sentiment: Dict[str, Any] = field(default_factory=lambda: {
        "positive_keywords": [],
        "negative_keywords": [],
        "overall_sentiment": "neutral",
    })
    call_tags: List[str] = field(default_factory=list)
    sales_audit_keywords: Dict[str, List[Dict[str, str]]] = field(
        default_factory=lambda: {
            "compliance_violations": [],
            "missed_opportunities": [],
            "pricing_discounts": [],
            "competitor_mentions": [],
            "customer_pain_points": [],
            "commitment_closing": [],
            "objection_handling": [],
            "negative_reactions": [],
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the result to a plain dictionary for JSON storage."""
        return {
            "quality_scores": [
                {
                    "parameter_name": qs.parameter_name,
                    "score": qs.score,
                    "justification": qs.justification,
                }
                for qs in self.quality_scores
            ],
            "overall_score": self.overall_score,
            "lead_intent_score": self.lead_intent_score,
            "intent_classification": self.intent_classification,
            "intent_signals": [
                {
                    "signal_name": sig.signal_name,
                    "detected": sig.detected,
                    "details": sig.details,
                }
                for sig in self.intent_signals
            ],
            "persona": {
                "type": self.persona.type,
                "budget_score": self.persona.budget_score,
                "authority_score": self.persona.authority_score,
                "need_score": self.persona.need_score,
                "timeline_score": self.persona.timeline_score,
                "discovery_insights": self.persona.discovery_insights,
            },
            "action_items": [
                {
                    "description": ai.description,
                    "category": ai.category,
                    "urgency": ai.urgency,
                }
                for ai in self.action_items
            ],
            "path_to_conversion": self.path_to_conversion,
            "rebuttals": self.rebuttals,
            "key_data_points": self.key_data_points,
            "follow_up_urgency": self.follow_up_urgency,
            "call_summary": self.call_summary,
            "escalation_keywords": self.escalation_keywords,
            "sentiment": self.sentiment,
            "call_tags": self.call_tags,
            "sales_audit_keywords": self.sales_audit_keywords,
        }


# ---------------------------------------------------------------------------
# Quality parameter / intent signal / persona type representations
# (these mirror the DB models but are simple dicts for decoupling)
# ---------------------------------------------------------------------------


@dataclass
class QualityParameterInput:
    """Minimal representation of a quality parameter for prompt rendering."""

    name: str
    description: str
    weight: float


@dataclass
class IntentSignalInput:
    """Minimal representation of an intent signal for prompt rendering."""

    name: str
    description: str


@dataclass
class PersonaTypeInput:
    """Minimal representation of a persona type for prompt rendering."""

    name: str
    description: str


# ---------------------------------------------------------------------------
# Main analyser class
# ---------------------------------------------------------------------------


class CallAnalyzer:
    """Analyses a sales call transcript using an LLM.

    The analyser renders a Jinja2 prompt template with the tenant's
    configurable parameters, sends it to the OpenAI API, and parses the
    structured JSON response.

    Parameters
    ----------
    model:
        The OpenAI model ID to use (default from ``settings.LLM_MODEL``).
    temperature:
        Sampling temperature.  Low values (0.1-0.3) are recommended for
        consistent structured output.
    max_tokens:
        Maximum response length.  Increase for very long transcripts.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.15,
        max_tokens: int = 4096,
    ) -> None:
        self.model = model or settings.LLM_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens

        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is not configured. "
                "Set the environment variable to use the LLM analysis service."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def analyze_call(
        self,
        transcript: str,
        quality_parameters: List[QualityParameterInput],
        intent_signals: List[IntentSignalInput],
        persona_types: List[PersonaTypeInput],
        db: Optional[Any] = None,
        tenant_id: Optional[Any] = None,
    ) -> AnalysisResult:
        """Analyse a transcript and return structured results.

        Parameters
        ----------
        transcript:
            The full call transcript text (ideally with speaker labels).
        quality_parameters:
            Scoring parameters to evaluate the call against.
        intent_signals:
            Intent signals to detect within the conversation.
        persona_types:
            Persona categories for lead classification.
        db:
            Optional database session for loading DB-stored prompt templates.
        tenant_id:
            Optional tenant UUID for loading tenant-specific prompts.

        Returns
        -------
        AnalysisResult
            Comprehensive analysis covering quality, intent, persona, and
            action items.

        Raises
        ------
        AnalysisError
            If the LLM call fails or returns unparseable output.
        """
        # 1. Render the prompt
        prompt_text = self._render_prompt(
            transcript=transcript,
            quality_parameters=quality_parameters,
            intent_signals=intent_signals,
            persona_types=persona_types,
            db=db,
            tenant_id=tenant_id,
        )

        # 2. Call the LLM
        raw_response = await self._call_llm(prompt_text)

        # 3. Parse into AnalysisResult
        return self._parse_response(raw_response)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _render_prompt(
        self,
        transcript: str,
        quality_parameters: List[QualityParameterInput],
        intent_signals: List[IntentSignalInput],
        persona_types: List[PersonaTypeInput],
        db: Optional[Any] = None,
        tenant_id: Optional[Any] = None,
    ) -> str:
        """Render the Jinja2 analysis prompt with the given context.

        If ``db`` and ``tenant_id`` are provided, checks the database for a
        tenant-specific prompt template first.  Falls back to the file-based
        Jinja2 template if no DB template is found.
        """
        if db is not None and tenant_id is not None:
            try:
                from app.models.prompt_template import PromptTemplate

                template_record = (
                    db.query(PromptTemplate)
                    .filter(
                        PromptTemplate.tenant_id == tenant_id,
                        PromptTemplate.name == "call_analysis",
                        PromptTemplate.is_active.is_(True),
                    )
                    .first()
                )
                if template_record:
                    env = Environment(autoescape=False, keep_trailing_newline=True)
                    template = env.from_string(template_record.template_content)
                    return template.render(
                        transcript=transcript,
                        quality_parameters=quality_parameters,
                        intent_signals=intent_signals,
                        persona_types=persona_types,
                    )
            except Exception:
                logger.warning(
                    "Failed to load DB prompt template for tenant %s, "
                    "falling back to file",
                    tenant_id,
                    exc_info=True,
                )

        # Fall back to file-based template
        template = _load_template("call_analysis.jinja2")
        return template.render(
            transcript=transcript,
            quality_parameters=quality_parameters,
            intent_signals=intent_signals,
            persona_types=persona_types,
        )

    async def _call_llm(self, prompt: str) -> str:
        """Send the rendered prompt to the OpenAI API and return the response.

        Uses the synchronous OpenAI client in a way that's compatible with
        async callers (the actual HTTP call is blocking but is wrapped by
        the retry decorator at the caller level).
        """
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AnalysisError(f"openai SDK is not installed: {exc}")

        logger.info(
            "Calling LLM model=%s temperature=%.2f max_tokens=%d",
            self.model,
            self.temperature,
            self.max_tokens,
        )

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert sales call analyst. "
                            "You always respond with valid JSON only — no markdown, "
                            "no code fences, no commentary."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if content is None:
                raise AnalysisError("LLM returned an empty response")

            logger.debug("LLM raw response length: %d chars", len(content))
            return content

        except AnalysisError:
            raise
        except Exception as exc:
            logger.exception("LLM call failed")
            raise AnalysisError(f"LLM call failed: {exc}") from exc

    def _parse_response(self, raw_json: str) -> AnalysisResult:
        """Parse the raw JSON string from the LLM into an ``AnalysisResult``.

        Handles common issues like markdown code fences, trailing commas,
        and missing fields gracefully.
        """
        # Strip markdown code fences if the model included them despite
        # instructions.
        cleaned = raw_json.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].rstrip()

        try:
            data: Dict[str, Any] = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON response: %s", exc)
            logger.debug("Raw response:\n%s", raw_json[:2000])
            raise AnalysisError(
                f"LLM returned invalid JSON: {exc}. "
                "The raw response has been logged for debugging."
            ) from exc

        return self._dict_to_result(data)

    @staticmethod
    def _dict_to_result(data: Dict[str, Any]) -> AnalysisResult:
        """Convert a validated dictionary into an ``AnalysisResult``."""
        # Quality scores
        quality_scores: List[QualityScore] = []
        for qs in data.get("quality_scores", []):
            quality_scores.append(
                QualityScore(
                    parameter_name=qs.get("parameter_name", "Unknown"),
                    score=float(qs.get("score", 0)),
                    justification=qs.get("justification", ""),
                )
            )

        # Intent signals
        intent_signals: List[IntentSignalResult] = []
        for sig in data.get("intent_signals", []):
            intent_signals.append(
                IntentSignalResult(
                    signal_name=sig.get("signal_name", "Unknown"),
                    detected=bool(sig.get("detected", False)),
                    details=sig.get("details", ""),
                )
            )

        # Persona
        persona_data = data.get("persona", {})
        persona = PersonaResult(
            type=persona_data.get("type", "Unknown"),
            budget_score=float(persona_data.get("budget_score", 0)),
            authority_score=float(persona_data.get("authority_score", 0)),
            need_score=float(persona_data.get("need_score", 0)),
            timeline_score=float(persona_data.get("timeline_score", 0)),
            discovery_insights=persona_data.get("discovery_insights", []),
        )

        # Action items
        action_items: List[ActionItem] = []
        for ai in data.get("action_items", []):
            action_items.append(
                ActionItem(
                    description=ai.get("description", ""),
                    category=ai.get("category", "other"),
                    urgency=ai.get("urgency", "this_week"),
                )
            )

        # Validate intent classification
        intent_classification = data.get("intent_classification", "cold").lower()
        if intent_classification not in ("hot", "warm", "cold"):
            intent_classification = "cold"

        # Validate follow-up urgency
        follow_up_urgency = data.get("follow_up_urgency", "this_week").lower()
        valid_urgencies = {"immediate", "this_week", "next_week", "nurture"}
        if follow_up_urgency not in valid_urgencies:
            follow_up_urgency = "this_week"

        # Escalation keywords
        raw_escalation = data.get("escalation_keywords", [])
        escalation_keywords: List[Dict[str, str]] = []
        if isinstance(raw_escalation, list):
            for ek in raw_escalation:
                if isinstance(ek, dict):
                    severity = ek.get("severity", "low").lower()
                    if severity not in ("high", "medium", "low"):
                        severity = "low"
                    escalation_keywords.append({
                        "keyword": ek.get("keyword", ""),
                        "context": ek.get("context", ""),
                        "severity": severity,
                    })

        # Sentiment
        raw_sentiment = data.get("sentiment", {})
        if isinstance(raw_sentiment, dict):
            overall_sentiment = raw_sentiment.get("overall_sentiment", "neutral").lower()
            if overall_sentiment not in ("positive", "negative", "mixed", "neutral"):
                overall_sentiment = "neutral"
            sentiment: Dict[str, Any] = {
                "positive_keywords": raw_sentiment.get("positive_keywords", []),
                "negative_keywords": raw_sentiment.get("negative_keywords", []),
                "overall_sentiment": overall_sentiment,
            }
        else:
            sentiment = {
                "positive_keywords": [],
                "negative_keywords": [],
                "overall_sentiment": "neutral",
            }

        # Call tags
        raw_tags = data.get("call_tags", [])
        call_tags: List[str] = []
        if isinstance(raw_tags, list):
            call_tags = [str(t) for t in raw_tags if isinstance(t, str)]

        # Sales audit keywords
        _AUDIT_CATEGORIES = {
            "compliance_violations",
            "missed_opportunities",
            "pricing_discounts",
            "competitor_mentions",
            "customer_pain_points",
            "commitment_closing",
            "objection_handling",
            "negative_reactions",
        }
        raw_audit = data.get("sales_audit_keywords", {})
        sales_audit_keywords: Dict[str, List[Dict[str, str]]] = {
            cat: [] for cat in _AUDIT_CATEGORIES
        }
        if isinstance(raw_audit, dict):
            for cat in _AUDIT_CATEGORIES:
                raw_list = raw_audit.get(cat, [])
                if isinstance(raw_list, list):
                    for item in raw_list:
                        if isinstance(item, dict):
                            sev = item.get("severity", "low").lower()
                            if sev not in ("high", "medium", "low"):
                                sev = "low"
                            sales_audit_keywords[cat].append({
                                "keyword": item.get("keyword", ""),
                                "context": item.get("context", ""),
                                "severity": sev,
                            })

        return AnalysisResult(
            quality_scores=quality_scores,
            overall_score=float(data.get("overall_score", 0)),
            lead_intent_score=float(data.get("lead_intent_score", 0)),
            intent_classification=intent_classification,
            intent_signals=intent_signals,
            persona=persona,
            action_items=action_items,
            path_to_conversion=data.get("path_to_conversion", ""),
            rebuttals=data.get("rebuttals", []),
            key_data_points=data.get("key_data_points", {}),
            follow_up_urgency=follow_up_urgency,
            call_summary=data.get("call_summary", ""),
            escalation_keywords=escalation_keywords,
            sentiment=sentiment,
            call_tags=call_tags,
            sales_audit_keywords=sales_audit_keywords,
        )


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class AnalysisError(Exception):
    """Raised when the call analysis pipeline encounters an error."""

    pass
