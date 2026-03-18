"""Tests for two-pass extraction (content + behavioral).

Verifies that splitting extraction into two focused LLM calls improves
recall on behavioral types (PSYCHOLOGICAL_SAFETY, MINDSET_SIGNAL, etc.)
that single-pass extraction tends to miss.
"""
import asyncio
import logging
from pathlib import Path

import pytest

from app.profiles import ProfileLoader, ExtractionProfile
from app.services.extraction.engine import ExtractionEngine, ExtractionResult

logger = logging.getLogger(__name__)

PROFILES_DIR = str(Path(__file__).parent.parent.parent / "app" / "profiles")

BEHAVIORAL_TYPES = {
    "FEEDBACK", "COACHING_MOMENT", "PSYCHOLOGICAL_SAFETY",
    "MINDSET_SIGNAL", "ACCOUNTABILITY_SIGNAL", "SENTIMENT",
}

TEST_TRANSCRIPT = """\
Sarah: Your code reviews have been really thorough lately, I appreciate the effort.
James: Thanks. Though honestly I just don't get the deployment pipeline. I'm not a DevOps person.
Sarah: That's a growth area, not a limitation. Try pairing with Priya on the next deploy."""

TEST_PARTICIPANTS = [
    {"externalId": "sarah-1", "name": "Sarah", "role": "manager"},
    {"externalId": "james-1", "name": "James", "role": "engineer"},
]


async def _run_extraction(
    profile: ExtractionProfile, mode: str,
) -> ExtractionResult:
    engine = ExtractionEngine(profile, extraction_mode=mode)
    return await engine.extract(TEST_TRANSCRIPT, TEST_PARTICIPANTS)


@pytest.fixture(scope="module")
def performance_profile() -> ExtractionProfile:
    loader = ProfileLoader(PROFILES_DIR)
    return loader.load("performance")


@pytest.fixture(scope="module")
def two_pass_result(performance_profile) -> ExtractionResult:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            _run_extraction(performance_profile, "two_pass")
        )
    finally:
        loop.close()


@pytest.fixture(scope="module")
def single_pass_result(performance_profile) -> ExtractionResult:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            _run_extraction(performance_profile, "single_pass")
        )
    finally:
        loop.close()


@pytest.mark.llm
def test_two_pass_produces_behavioral_types(two_pass_result):
    """Two-pass extraction should detect at least 1 behavioral type from a
    conversation containing coaching, mindset signals, and recognition."""
    found_types = {
        item.extraction_type for item in two_pass_result.extractions
    }
    behavioral_found = found_types & BEHAVIORAL_TYPES

    logger.info(
        "Two-pass found types: %s (behavioral: %s)",
        found_types, behavioral_found,
    )

    assert len(behavioral_found) >= 1, (
        f"Two-pass extraction found no behavioral types. "
        f"All found types: {found_types}"
    )

    # Specifically check for the subtle types that single-pass misses
    subtle_types = {"COACHING_MOMENT", "MINDSET_SIGNAL", "PSYCHOLOGICAL_SAFETY"}
    subtle_found = found_types & subtle_types
    logger.info("Subtle behavioral types found: %s", subtle_found)
    # At least 1 of the 3 subtle types should be detected
    assert len(subtle_found) >= 1, (
        f"Two-pass extraction missed all subtle behavioral types. "
        f"Expected at least 1 of {subtle_types}, found: {found_types}"
    )


@pytest.mark.llm
def test_single_pass_baseline(single_pass_result):
    """Single-pass baseline — log what it finds for comparison.

    This test does not assert behavioral types are found (they often aren't
    in single-pass). It serves as a comparison point for two-pass improvements.
    """
    found_types = {
        item.extraction_type for item in single_pass_result.extractions
    }
    behavioral_found = found_types & BEHAVIORAL_TYPES

    logger.info(
        "Single-pass found types: %s (behavioral: %s, total extractions: %d)",
        found_types, behavioral_found, len(single_pass_result.extractions),
    )

    # Minimal assertion: single-pass should at least return valid results
    assert single_pass_result.tokens_used > 0
    assert single_pass_result.model_used is not None
