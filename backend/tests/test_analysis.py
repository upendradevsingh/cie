"""Tests for LLM analyzer with mocked OpenAI, response parsing."""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.analysis.llm_analyzer import (
    AnalysisError,
    AnalysisResult,
    CallAnalyzer,
    QualityParameterInput,
    IntentSignalInput,
    PersonaTypeInput,
)
from tests.fixtures.analysis_results import (
    HOT_LEAD_ANALYSIS,
    WARM_LEAD_ANALYSIS,
    COLD_LEAD_ANALYSIS,
    analysis_as_json,
    analysis_with_code_fences,
)
from tests.fixtures.transcripts import (
    SOLAR_HOT_LEAD_RAW,
    SAAS_WARM_LEAD_RAW,
    COLD_CALL_RAW,
)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Standard test inputs
_QUALITY_PARAMS = [
    QualityParameterInput("Opening & Greeting", "Proper intro", 1.0),
    QualityParameterInput("Need Discovery", "Probing questions", 1.0),
    QualityParameterInput("Product Knowledge", "Accurate info", 1.0),
]
_INTENT_SIGNALS = [
    IntentSignalInput("Budget Mentioned", "Customer mentioned budget"),
    IntentSignalInput("Timeline Discussed", "Timeline discussed"),
]
_PERSONA_TYPES = [
    PersonaTypeInput("Ready Buyer", "High intent buyer"),
    PersonaTypeInput("Evaluator", "Still evaluating"),
]


def _mock_openai_response(content: str):
    """Create a mock OpenAI chat completion response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response


class TestAnalyzerSuccess:
    """Happy-path tests for the analyzer."""

    def test_analyzer_success_hot_lead(self):
        """Full analysis of hot lead transcript."""
        analyzer = CallAnalyzer()

        with patch("openai.OpenAI") as MockOAI:
            mock_client = MagicMock()
            MockOAI.return_value = mock_client
            mock_client.chat.completions.create.return_value = _mock_openai_response(
                analysis_as_json(HOT_LEAD_ANALYSIS)
            )

            result = _run(analyzer.analyze_call(
                SOLAR_HOT_LEAD_RAW,
                _QUALITY_PARAMS,
                _INTENT_SIGNALS,
                _PERSONA_TYPES,
            ))

        assert isinstance(result, AnalysisResult)
        assert result.overall_score == 85.5
        assert result.intent_classification == "hot"
        assert result.lead_intent_score == 88.0
        assert len(result.quality_scores) == 10
        assert len(result.intent_signals) == 8
        assert len(result.action_items) == 4
        assert result.persona.type == "Ready Buyer"

    def test_analyzer_success_warm_lead(self):
        """Full analysis of warm lead transcript."""
        analyzer = CallAnalyzer()

        with patch("openai.OpenAI") as MockOAI:
            mock_client = MagicMock()
            MockOAI.return_value = mock_client
            mock_client.chat.completions.create.return_value = _mock_openai_response(
                analysis_as_json(WARM_LEAD_ANALYSIS)
            )

            result = _run(analyzer.analyze_call(
                SAAS_WARM_LEAD_RAW,
                _QUALITY_PARAMS,
                _INTENT_SIGNALS,
                _PERSONA_TYPES,
            ))

        assert result.intent_classification == "warm"
        assert result.overall_score == 58.0
        assert result.persona.authority_score == 3.0

    def test_analyzer_success_cold_lead(self):
        """Full analysis of cold lead transcript."""
        analyzer = CallAnalyzer()

        with patch("openai.OpenAI") as MockOAI:
            mock_client = MagicMock()
            MockOAI.return_value = mock_client
            mock_client.chat.completions.create.return_value = _mock_openai_response(
                analysis_as_json(COLD_LEAD_ANALYSIS)
            )

            result = _run(analyzer.analyze_call(
                COLD_CALL_RAW,
                _QUALITY_PARAMS,
                _INTENT_SIGNALS,
                _PERSONA_TYPES,
            ))

        assert result.intent_classification == "cold"
        assert result.overall_score == 37.0
        assert result.follow_up_urgency == "nurture"


class TestAnalyzerParsing:
    """Edge cases in response parsing."""

    def test_analyzer_json_with_code_fences(self):
        """LLM wraps response in ```json``` fences — still parses."""
        analyzer = CallAnalyzer()

        with patch("openai.OpenAI") as MockOAI:
            mock_client = MagicMock()
            MockOAI.return_value = mock_client
            mock_client.chat.completions.create.return_value = _mock_openai_response(
                analysis_with_code_fences(HOT_LEAD_ANALYSIS)
            )

            result = _run(analyzer.analyze_call(
                SOLAR_HOT_LEAD_RAW,
                _QUALITY_PARAMS,
                _INTENT_SIGNALS,
                _PERSONA_TYPES,
            ))

        assert result.overall_score == 85.5

    def test_analyzer_invalid_json(self):
        """Invalid JSON raises AnalysisError."""
        analyzer = CallAnalyzer()

        with patch("openai.OpenAI") as MockOAI:
            mock_client = MagicMock()
            MockOAI.return_value = mock_client
            mock_client.chat.completions.create.return_value = _mock_openai_response(
                "This is not valid JSON at all"
            )

            with pytest.raises(AnalysisError, match="invalid JSON"):
                _run(analyzer.analyze_call(
                    "test transcript",
                    _QUALITY_PARAMS,
                    _INTENT_SIGNALS,
                    _PERSONA_TYPES,
                ))

    def test_analyzer_empty_response(self):
        """Empty response raises AnalysisError."""
        analyzer = CallAnalyzer()

        with patch("openai.OpenAI") as MockOAI:
            mock_client = MagicMock()
            MockOAI.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock()]
            mock_resp.choices[0].message.content = None
            mock_client.chat.completions.create.return_value = mock_resp

            with pytest.raises(AnalysisError, match="empty response"):
                _run(analyzer.analyze_call(
                    "test transcript",
                    _QUALITY_PARAMS,
                    _INTENT_SIGNALS,
                    _PERSONA_TYPES,
                ))

    def test_analyzer_missing_fields(self):
        """Missing fields get graceful defaults."""
        analyzer = CallAnalyzer()
        minimal_json = json.dumps({"overall_score": 50})

        with patch("openai.OpenAI") as MockOAI:
            mock_client = MagicMock()
            MockOAI.return_value = mock_client
            mock_client.chat.completions.create.return_value = _mock_openai_response(minimal_json)

            result = _run(analyzer.analyze_call(
                "test transcript",
                _QUALITY_PARAMS,
                _INTENT_SIGNALS,
                _PERSONA_TYPES,
            ))

        assert result.overall_score == 50
        assert result.quality_scores == []
        assert result.intent_signals == []
        assert result.action_items == []
        assert result.intent_classification == "cold"
        assert result.follow_up_urgency == "this_week"

    def test_analyzer_score_clamping(self):
        """Scores outside valid range are handled by _dict_to_result defaults."""
        analyzer = CallAnalyzer()
        # The analyzer doesn't clamp in _dict_to_result but passes through
        data = {
            "overall_score": 150,
            "lead_intent_score": -10,
            "quality_scores": [
                {"parameter_name": "Test", "score": 15, "justification": "Over max"},
            ],
        }

        with patch("openai.OpenAI") as MockOAI:
            mock_client = MagicMock()
            MockOAI.return_value = mock_client
            mock_client.chat.completions.create.return_value = _mock_openai_response(
                json.dumps(data)
            )

            result = _run(analyzer.analyze_call(
                "test",
                _QUALITY_PARAMS,
                _INTENT_SIGNALS,
                _PERSONA_TYPES,
            ))

        # The analyzer stores the raw values; clamping happens at persistence
        assert result.overall_score == 150
        assert result.quality_scores[0].score == 15

    def test_analyzer_invalid_intent_classification(self):
        """Invalid intent falls back to 'cold'."""
        analyzer = CallAnalyzer()
        data = {"intent_classification": "INVALID_VALUE"}

        with patch("openai.OpenAI") as MockOAI:
            mock_client = MagicMock()
            MockOAI.return_value = mock_client
            mock_client.chat.completions.create.return_value = _mock_openai_response(
                json.dumps(data)
            )

            result = _run(analyzer.analyze_call(
                "test",
                _QUALITY_PARAMS,
                _INTENT_SIGNALS,
                _PERSONA_TYPES,
            ))

        assert result.intent_classification == "cold"

    def test_analyzer_invalid_urgency(self):
        """Invalid urgency falls back to 'this_week'."""
        analyzer = CallAnalyzer()
        data = {"follow_up_urgency": "ASAP_NOW"}

        with patch("openai.OpenAI") as MockOAI:
            mock_client = MagicMock()
            MockOAI.return_value = mock_client
            mock_client.chat.completions.create.return_value = _mock_openai_response(
                json.dumps(data)
            )

            result = _run(analyzer.analyze_call(
                "test",
                _QUALITY_PARAMS,
                _INTENT_SIGNALS,
                _PERSONA_TYPES,
            ))

        assert result.follow_up_urgency == "this_week"


class TestAnalyzerPrompt:
    """Template rendering tests."""

    def test_prompt_rendering(self):
        """Verify Jinja2 template renders with all params."""
        analyzer = CallAnalyzer()
        rendered = analyzer._render_prompt(
            transcript="Agent: Hello\nCustomer: Hi",
            quality_parameters=_QUALITY_PARAMS,
            intent_signals=_INTENT_SIGNALS,
            persona_types=_PERSONA_TYPES,
        )
        assert "Opening & Greeting" in rendered
        assert "Budget Mentioned" in rendered
        assert "Ready Buyer" in rendered
        assert "Agent: Hello" in rendered


class TestAnalyzerInit:
    """Initialization tests."""

    def test_analyzer_no_api_key(self):
        """Missing API key raises ValueError."""
        import app.config
        original = app.config.settings.OPENAI_API_KEY
        try:
            app.config.settings.OPENAI_API_KEY = ""
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                CallAnalyzer()
        finally:
            app.config.settings.OPENAI_API_KEY = original
