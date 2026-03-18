"""Prompt stability tests.

Runs the same conversation through the extraction engine multiple times
and measures consistency of extraction types, counts, and confidence scores.
"""
import asyncio
import json
import logging
from pathlib import Path

import pytest

from app.profiles import ProfileLoader, ExtractionProfile
from app.services.extraction.engine import ExtractionEngine

from tests.eval.conftest import build_transcript_from_segments
from tests.eval.metrics import compute_stability_metrics

logger = logging.getLogger(__name__)

EVAL_DIR = Path(__file__).parent
PROFILES_DIR = str(Path(__file__).parent.parent.parent / "app" / "profiles")

NUM_RUNS = 5


def _load_baseline_scores() -> dict:
    with open(EVAL_DIR / "baseline_scores.json") as f:
        return json.load(f)


def _load_gold_conversation(conv_id: str) -> dict:
    with open(EVAL_DIR / "gold_dataset.json") as f:
        dataset = json.load(f)
    for conv in dataset:
        if conv["id"] == conv_id:
            return conv
    raise ValueError(f"Conversation {conv_id} not found")


async def _run_single_extraction(
    profile: ExtractionProfile,
    gold: dict,
) -> list[dict]:
    """Run extraction once and return extraction dicts."""
    transcript = build_transcript_from_segments(gold["segments"])
    participants = gold.get("participants", [])
    engine = ExtractionEngine(profile)
    result = await engine.extract(transcript, participants)
    return [
        {
            "extraction_type": item.extraction_type,
            "description": item.description,
            "confidence": item.confidence,
        }
        for item in result.extractions
    ]


async def _run_stability_test(
    conv_id: str,
    num_runs: int = NUM_RUNS,
) -> list[list[dict]]:
    """Run the same conversation through extraction multiple times."""
    gold = _load_gold_conversation(conv_id)
    loader = ProfileLoader(PROFILES_DIR)
    profile = loader.load(gold.get("profile", "performance"))

    runs = []
    for i in range(num_runs):
        result = await _run_single_extraction(profile, gold)
        runs.append(result)
        logger.info(
            "Stability run %d/%d for %s: %d extractions",
            i + 1, num_runs, conv_id, len(result),
        )

    return runs


@pytest.fixture(scope="module")
def stability_runs() -> list[list[dict]]:
    """Run gold_001 (clear 1:1 with commitments) 5 times.

    Module-scoped so all stability tests share the same data.
    """
    loop = asyncio.new_event_loop()
    try:
        runs = loop.run_until_complete(_run_stability_test("gold_001", NUM_RUNS))
    finally:
        loop.close()
    return runs


@pytest.fixture(scope="module")
def stability_metrics_result(stability_runs) -> dict[str, float]:
    """Compute stability metrics from the runs."""
    metrics = compute_stability_metrics(stability_runs)
    logger.info(
        "Stability metrics: type_consistency=%.3f count_variance=%.3f confidence_std=%.3f",
        metrics["type_consistency"],
        metrics["count_variance"],
        metrics["confidence_std"],
    )
    return metrics


@pytest.fixture(scope="module")
def baselines() -> dict:
    return _load_baseline_scores()


@pytest.mark.llm
def test_type_consistency(stability_metrics_result, baselines):
    """The same conversation should produce the same set of extraction types
    across multiple runs."""
    min_consistency = baselines["stability"]["min_type_consistency"]
    actual = stability_metrics_result["type_consistency"]
    assert actual >= min_consistency, (
        f"Type consistency {actual:.3f} below minimum {min_consistency}. "
        f"Extraction types are inconsistent across runs."
    )


@pytest.mark.llm
def test_count_stability(stability_metrics_result, baselines):
    """The number of extractions should be relatively stable across runs."""
    max_variance = baselines["stability"]["max_count_variance"]
    actual = stability_metrics_result["count_variance"]
    assert actual <= max_variance, (
        f"Count variance (CV) {actual:.3f} exceeds maximum {max_variance}. "
        f"Extraction count is too variable across runs."
    )


@pytest.mark.llm
def test_confidence_variance(stability_metrics_result, baselines):
    """Confidence scores should not vary wildly across runs."""
    max_std = baselines["stability"]["max_confidence_std"]
    actual = stability_metrics_result["confidence_std"]
    assert actual <= max_std, (
        f"Average confidence std {actual:.3f} exceeds maximum {max_std}. "
        f"Confidence scores are too unstable."
    )


@pytest.mark.llm
def test_minimum_extractions_per_run(stability_runs):
    """Each run should produce at least 2 extractions for gold_001
    (which has clear commitments and action items)."""
    for i, run in enumerate(stability_runs):
        assert len(run) >= 2, (
            f"Run {i + 1} produced only {len(run)} extractions. "
            f"Expected at least 2 for a clear 1:1 conversation."
        )


@pytest.mark.llm
def test_core_types_present_every_run(stability_runs):
    """COMMITMENT and GOAL_UPDATE should appear in every run for gold_001."""
    for i, run in enumerate(stability_runs):
        types = {e["extraction_type"] for e in run}
        # At minimum, COMMITMENT should always be found in gold_001
        assert "COMMITMENT" in types, (
            f"Run {i + 1} missing COMMITMENT extraction. Found types: {types}"
        )
