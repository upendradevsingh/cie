"""Fast unit tests for _parse_extractions and build_extraction_prompt.

No LLM calls. Tests parsing logic, prompt construction, and edge cases.
"""
import pytest

from app.profiles import ProfileLoader, ExtractionProfile
from app.services.extraction.engine import ExtractionEngine, ExtractedItem
from app.services.extraction.prompts import build_extraction_prompt, SYSTEM_PROMPT

PROFILES_DIR = str(__import__("pathlib").Path(__file__).parent.parent.parent / "app" / "profiles")


@pytest.fixture
def profile() -> ExtractionProfile:
    loader = ProfileLoader(PROFILES_DIR)
    return loader.load("performance")


@pytest.fixture
def engine(profile: ExtractionProfile) -> ExtractionEngine:
    return ExtractionEngine(profile)


@pytest.fixture
def sample_participants() -> list[dict]:
    return [
        {"externalId": "u1", "name": "Alice", "role": "manager"},
        {"externalId": "u2", "name": "Bob", "role": "engineer"},
    ]


# --- _parse_extractions tests ---


@pytest.mark.fast
def test_parse_valid_extractions(engine: ExtractionEngine):
    raw = {
        "extractions": [
            {
                "extraction_type": "COMMITMENT",
                "description": "Alice will deliver the report by Friday",
                "confidence": 0.92,
                "attributed_to": {"externalId": "u1", "name": "Alice"},
                "evidence": "I will deliver the report by Friday",
                "attributes": {"deadline": "Friday", "specificity": "high"},
            }
        ]
    }
    items = engine._parse_extractions(raw)
    assert len(items) == 1
    assert items[0].extraction_type == "COMMITMENT"
    assert items[0].confidence == 0.92
    assert items[0].attributes["specificity"] == "high"


@pytest.mark.fast
def test_parse_empty_extractions(engine: ExtractionEngine):
    raw = {"extractions": []}
    items = engine._parse_extractions(raw)
    assert items == []


@pytest.mark.fast
def test_parse_missing_extractions_key(engine: ExtractionEngine):
    raw = {"summary": "No extractions found"}
    items = engine._parse_extractions(raw)
    assert items == []


@pytest.mark.fast
def test_parse_none_items_skipped(engine: ExtractionEngine):
    raw = {
        "extractions": [
            None,
            {"extraction_type": "BLOCKER", "description": "Valid", "confidence": 0.8, "attributes": {}},
            None,
        ]
    }
    items = engine._parse_extractions(raw)
    assert len(items) == 1
    assert items[0].extraction_type == "BLOCKER"


@pytest.mark.fast
def test_parse_malformed_items_skipped(engine: ExtractionEngine):
    raw = {
        "extractions": [
            {"extraction_type": "COMMITMENT", "description": "Good", "confidence": 0.9, "attributes": {}},
            {"completely": "wrong", "format": True},
        ]
    }
    items = engine._parse_extractions(raw)
    # The malformed item will parse with defaults (extraction_type=UNKNOWN, confidence=0.0)
    # so it won't be skipped by _parse_extractions itself; it just gets defaults
    assert len(items) == 2
    assert items[0].extraction_type == "COMMITMENT"
    assert items[1].extraction_type == "UNKNOWN"


@pytest.mark.fast
def test_parse_type_normalized_to_uppercase(engine: ExtractionEngine):
    raw = {
        "extractions": [
            {"extraction_type": "commitment", "description": "Test", "confidence": 0.85, "attributes": {}},
            {"extraction_type": "Blocker", "description": "Test2", "confidence": 0.80, "attributes": {}},
        ]
    }
    items = engine._parse_extractions(raw)
    assert items[0].extraction_type == "COMMITMENT"
    assert items[1].extraction_type == "BLOCKER"


@pytest.mark.fast
def test_parse_missing_optional_fields(engine: ExtractionEngine):
    raw = {
        "extractions": [
            {"extraction_type": "FEEDBACK", "description": "Good work", "confidence": 0.75},
        ]
    }
    items = engine._parse_extractions(raw)
    assert len(items) == 1
    assert items[0].attributed_to is None
    assert items[0].evidence is None
    assert items[0].attributes == {}


@pytest.mark.fast
def test_parse_confidence_as_string(engine: ExtractionEngine):
    raw = {
        "extractions": [
            {"extraction_type": "DECISION", "description": "Test", "confidence": "0.88", "attributes": {}},
        ]
    }
    items = engine._parse_extractions(raw)
    assert len(items) == 1
    assert items[0].confidence == 0.88


@pytest.mark.fast
def test_parse_invalid_confidence_skipped(engine: ExtractionEngine):
    raw = {
        "extractions": [
            {"extraction_type": "DECISION", "description": "Test", "confidence": "not_a_number", "attributes": {}},
        ]
    }
    items = engine._parse_extractions(raw)
    # Should be skipped due to ValueError on float conversion
    assert len(items) == 0


# --- build_extraction_prompt tests ---


@pytest.mark.fast
def test_prompt_includes_all_enabled_types(profile: ExtractionProfile, sample_participants: list):
    prompt = build_extraction_prompt(profile, "Test transcript", sample_participants)
    for ext_type in profile.enabled_types():
        assert ext_type in prompt


@pytest.mark.fast
def test_prompt_includes_transcript(profile: ExtractionProfile, sample_participants: list):
    transcript = "Manager: I will deliver the API by Friday.\nEngineer: I am blocked on credentials."
    prompt = build_extraction_prompt(profile, transcript, sample_participants)
    assert transcript in prompt


@pytest.mark.fast
def test_prompt_includes_participants_json(profile: ExtractionProfile, sample_participants: list):
    prompt = build_extraction_prompt(profile, "Test", sample_participants)
    assert '"Alice"' in prompt
    assert '"Bob"' in prompt
    assert '"manager"' in prompt


@pytest.mark.fast
def test_prompt_includes_confidence_thresholds(profile: ExtractionProfile, sample_participants: list):
    prompt = build_extraction_prompt(profile, "Test", sample_participants)
    # COMMITMENT threshold is 0.80
    assert "0.8" in prompt or "0.80" in prompt
    # BLOCKER threshold is 0.75
    assert "0.75" in prompt


@pytest.mark.fast
def test_prompt_includes_attribute_definitions(profile: ExtractionProfile, sample_participants: list):
    prompt = build_extraction_prompt(profile, "Test", sample_participants)
    assert "deadline" in prompt
    assert "severity" in prompt
    assert "recipient" in prompt
    assert "specificity" in prompt


@pytest.mark.fast
def test_prompt_includes_response_format(profile: ExtractionProfile, sample_participants: list):
    prompt = build_extraction_prompt(profile, "Test", sample_participants)
    assert "extraction_type" in prompt
    assert "description" in prompt
    assert "confidence" in prompt
    assert "evidence" in prompt
    assert "summary" in prompt


@pytest.mark.fast
def test_system_prompt_contains_rules():
    assert "confidence" in SYSTEM_PROMPT.lower()
    assert "json" in SYSTEM_PROMPT.lower()
    assert "extract" in SYSTEM_PROMPT.lower()
