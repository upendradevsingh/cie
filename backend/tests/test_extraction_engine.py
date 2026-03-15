"""Tests for the extraction engine (mocked LLM calls)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.profiles import ProfileLoader, ExtractionProfile
from app.services.extraction.engine import ExtractionEngine, ExtractionResult, ExtractedItem
from app.services.extraction.prompts import build_extraction_prompt

PROFILES_DIR = str(__import__('pathlib').Path(__file__).parent.parent / "app" / "profiles")


@pytest.fixture
def performance_profile() -> ExtractionProfile:
    loader = ProfileLoader(PROFILES_DIR)
    return loader.load("performance")


@pytest.fixture
def sample_transcript() -> str:
    return """
Manager: How are things going with the Q2 roadmap?
Engineer: We're making progress, but I'm blocked on the API credentials from the infra team.
Manager: I'll get you those credentials by end of day tomorrow.
Engineer: Great, I'll have the integration done by Friday then.
Manager: Good. How are you feeling about the workload overall?
Engineer: Honestly a bit overwhelmed, but manageable.
"""


@pytest.fixture
def sample_participants() -> list:
    return [
        {"externalId": "mgr1", "name": "Alice", "role": "manager"},
        {"externalId": "eng1", "name": "Bob", "role": "engineer"},
    ]


def test_build_prompt_includes_extraction_types(performance_profile, sample_transcript, sample_participants):
    prompt = build_extraction_prompt(performance_profile, sample_transcript, sample_participants)
    assert "COMMITMENT" in prompt
    assert "BLOCKER" in prompt
    assert "FEEDBACK" in prompt
    assert "Performance Management" in prompt
    assert sample_transcript in prompt


def test_build_prompt_includes_thresholds(performance_profile, sample_transcript, sample_participants):
    prompt = build_extraction_prompt(performance_profile, sample_transcript, sample_participants)
    assert "0.8" in prompt or "0.80" in prompt


@pytest.mark.asyncio
async def test_extract_with_mocked_llm(performance_profile, sample_transcript, sample_participants):
    mock_response = {
        "extractions": [
            {
                "extraction_type": "COMMITMENT",
                "description": "Manager will provide API credentials by end of day tomorrow",
                "confidence": 0.92,
                "attributed_to": {"externalId": "mgr1", "name": "Alice", "role": "manager"},
                "evidence": "I'll get you those credentials by end of day tomorrow",
                "attributes": {"deadline": "tomorrow", "specificity": "high"},
            },
            {
                "extraction_type": "BLOCKER",
                "description": "Engineer blocked on API credentials from infra team",
                "confidence": 0.88,
                "attributed_to": {"externalId": "eng1", "name": "Bob", "role": "engineer"},
                "evidence": "I'm blocked on the API credentials from the infra team",
                "attributes": {"severity": "medium", "blocked_by": "infra team", "status": "open"},
            },
            {
                "extraction_type": "SENTIMENT",
                "description": "Engineer feels overwhelmed but managing",
                "confidence": 0.55,  # Below SENTIMENT threshold of 0.60 — should be filtered
                "attributed_to": None,
                "evidence": "Honestly a bit overwhelmed, but manageable",
                "attributes": {"score": 2.5, "energy_level": "low"},
            },
        ],
        "summary": "Manager committed to providing API credentials; engineer blocked pending those credentials."
    }

    engine = ExtractionEngine(performance_profile)

    with patch.object(engine, "_call_llm", new=AsyncMock(return_value=mock_response)):
        result = await engine.extract(sample_transcript, sample_participants)

    assert isinstance(result, ExtractionResult)
    # SENTIMENT with confidence 0.55 < threshold 0.60 should be filtered out
    assert len(result.extractions) == 2
    types = {e.extraction_type for e in result.extractions}
    assert "COMMITMENT" in types
    assert "BLOCKER" in types
    assert "SENTIMENT" not in types
    assert "credentials" in result.summary.lower()


@pytest.mark.asyncio
async def test_extract_handles_empty_response(performance_profile, sample_transcript, sample_participants):
    mock_response = {"extractions": [], "summary": "No significant extractions."}
    engine = ExtractionEngine(performance_profile)

    with patch.object(engine, "_call_llm", new=AsyncMock(return_value=mock_response)):
        result = await engine.extract(sample_transcript, sample_participants)

    assert result.extractions == []
    assert result.summary == "No significant extractions."


@pytest.mark.asyncio
async def test_extract_handles_malformed_items(performance_profile, sample_transcript, sample_participants):
    mock_response = {
        "extractions": [
            {"extraction_type": "COMMITMENT", "description": "Valid item", "confidence": 0.9, "attributes": {}},
            {"broken": True},  # Missing required fields — should be skipped
            None,  # None item — should be skipped
        ],
        "summary": "Test"
    }
    engine = ExtractionEngine(performance_profile)

    with patch.object(engine, "_call_llm", new=AsyncMock(return_value=mock_response)):
        result = await engine.extract(sample_transcript, sample_participants)

    # Only the valid item should be in results
    assert len(result.extractions) == 1


def test_parse_extractions_filters_by_threshold(performance_profile):
    engine = ExtractionEngine(performance_profile)
    raw = {
        "extractions": [
            {"extraction_type": "COMMITMENT", "description": "High confidence", "confidence": 0.95, "attributes": {}},
            {"extraction_type": "COMMITMENT", "description": "Low confidence", "confidence": 0.50, "attributes": {}},
        ]
    }
    items = engine._parse_extractions(raw)
    # COMMITMENT threshold is 0.80
    filtered = [i for i in items if i.confidence >= performance_profile.get_threshold(i.extraction_type)]
    assert len(filtered) == 1
    assert filtered[0].description == "High confidence"
