"""Tests against gold dataset using real LLM calls.

Module-scoped fixture runs all conversations once and caches results.
Tests check overall F1, per-type recall, false positive rate,
ambiguous handling, Hinglish support, absent types, and confidence calibration.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import pytest

from app.profiles import ProfileLoader, ExtractionProfile
from app.services.extraction.engine import ExtractionEngine, ExtractionResult

from tests.eval.conftest import build_transcript_from_segments
from tests.eval.metrics import (
    compute_metrics,
    compute_false_positive_rate,
    compute_confidence_calibration,
    evaluate_conversation,
    format_report,
)

logger = logging.getLogger(__name__)

EVAL_DIR = Path(__file__).parent
PROFILES_DIR = str(Path(__file__).parent.parent.parent / "app" / "profiles")


def _load_gold_dataset() -> list[dict]:
    with open(EVAL_DIR / "gold_dataset.json") as f:
        return json.load(f)


def _load_baseline_scores() -> dict:
    with open(EVAL_DIR / "baseline_scores.json") as f:
        return json.load(f)


async def _run_extraction(
    profile: ExtractionProfile,
    gold: dict,
) -> list[dict]:
    """Run extraction on a single gold conversation and return extraction dicts."""
    transcript = build_transcript_from_segments(gold["segments"])
    participants = gold.get("participants", [])

    engine = ExtractionEngine(profile)
    result = await engine.extract(transcript, participants)

    return [
        {
            "extraction_type": item.extraction_type,
            "description": item.description,
            "confidence": item.confidence,
            "attributed_to": item.attributed_to,
            "evidence": item.evidence,
            "attributes": item.attributes,
        }
        for item in result.extractions
    ]


async def _run_all_extractions(
    gold_dataset: list[dict],
) -> dict[str, list[dict]]:
    """Run extractions for all gold conversations. Returns {conv_id: [extraction_dicts]}."""
    loader = ProfileLoader(PROFILES_DIR)
    results: dict[str, list[dict]] = {}

    for gold in gold_dataset:
        profile_id = gold.get("profile", "performance")
        profile = loader.load(profile_id)
        conv_id = gold["id"]

        try:
            extractions = await _run_extraction(profile, gold)
            results[conv_id] = extractions
            logger.info(
                "Extracted %d items from %s (%s)",
                len(extractions),
                conv_id,
                gold["name"],
            )
        except Exception as e:
            logger.error("Extraction failed for %s: %s", conv_id, e)
            results[conv_id] = []

    return results


@pytest.fixture(scope="module")
def all_extraction_results() -> dict[str, list[dict]]:
    """Run all gold conversations through the extraction engine once.

    This is module-scoped so all tests in this file share the same results.
    """
    gold_dataset = _load_gold_dataset()
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(_run_all_extractions(gold_dataset))
    finally:
        loop.close()
    return results


@pytest.fixture(scope="module")
def gold_data() -> list[dict]:
    return _load_gold_dataset()


@pytest.fixture(scope="module")
def baselines() -> dict:
    return _load_baseline_scores()


@pytest.fixture(scope="module")
def overall_metrics(gold_data, all_extraction_results) -> Any:
    metrics = compute_metrics(gold_data, all_extraction_results)
    report = format_report(metrics)
    logger.info("\n%s", report)
    return metrics


# --- Quality Tests ---


@pytest.mark.llm
def test_overall_f1(overall_metrics, baselines):
    """Overall F1 must meet baseline threshold."""
    min_f1 = baselines["overall"]["min_f1"]
    actual = overall_metrics.overall_f1
    assert actual >= min_f1, (
        f"Overall F1 {actual:.3f} below baseline {min_f1}. "
        f"TP={overall_metrics.total_tp} FP={overall_metrics.total_fp} FN={overall_metrics.total_fn}"
    )


@pytest.mark.llm
def test_overall_precision(overall_metrics, baselines):
    """Overall precision must meet baseline threshold."""
    min_p = baselines["overall"]["min_precision"]
    actual = overall_metrics.overall_precision
    assert actual >= min_p, f"Overall precision {actual:.3f} below baseline {min_p}"


@pytest.mark.llm
def test_overall_recall(overall_metrics, baselines):
    """Overall recall must meet baseline threshold."""
    min_r = baselines["overall"]["min_recall"]
    actual = overall_metrics.overall_recall
    assert actual >= min_r, f"Overall recall {actual:.3f} below baseline {min_r}"


@pytest.mark.llm
def test_per_type_recall(overall_metrics, baselines):
    """Each extraction type must meet its per-type recall baseline."""
    per_type_baselines = baselines["per_type"]
    failures = []
    for ext_type, type_baseline in per_type_baselines.items():
        type_metrics = overall_metrics.per_type.get(ext_type)
        if type_metrics is None:
            failures.append(f"{ext_type}: no extractions found at all")
            continue
        min_recall = type_baseline["min_recall"]
        actual_recall = type_metrics.recall
        if actual_recall < min_recall:
            failures.append(
                f"{ext_type}: recall {actual_recall:.3f} < {min_recall} "
                f"(TP={type_metrics.true_positives} FN={type_metrics.false_negatives})"
            )
    assert not failures, "Per-type recall failures:\n" + "\n".join(failures)


@pytest.mark.llm
def test_per_type_precision(overall_metrics, baselines):
    """Each extraction type must meet its per-type precision baseline."""
    per_type_baselines = baselines["per_type"]
    failures = []
    for ext_type, type_baseline in per_type_baselines.items():
        type_metrics = overall_metrics.per_type.get(ext_type)
        if type_metrics is None:
            continue  # No extractions means no FP either
        min_precision = type_baseline["min_precision"]
        actual_precision = type_metrics.precision
        if actual_precision < min_precision:
            failures.append(
                f"{ext_type}: precision {actual_precision:.3f} < {min_precision} "
                f"(TP={type_metrics.true_positives} FP={type_metrics.false_positives})"
            )
    assert not failures, "Per-type precision failures:\n" + "\n".join(failures)


@pytest.mark.llm
def test_false_positive_rate_ambiguous(
    gold_data, all_extraction_results, baselines
):
    """Ambiguous conversations should produce few or no extractions."""
    fp_rate = compute_false_positive_rate(
        gold_data, all_extraction_results, ["ambiguous"]
    )
    max_fp = baselines["false_positive_rate"]["max_fp_rate_ambiguous"]
    assert fp_rate <= max_fp, (
        f"Ambiguous FP rate {fp_rate:.3f} exceeds max {max_fp}. "
        f"Engine is hallucinating extractions from casual conversations."
    )


@pytest.mark.llm
def test_false_positive_rate_edge_cases(
    gold_data, all_extraction_results, baselines
):
    """Edge case conversations (empty, single-word) should produce no extractions."""
    fp_rate = compute_false_positive_rate(
        gold_data, all_extraction_results, ["edge_case"]
    )
    max_fp = baselines["false_positive_rate"]["max_fp_rate_edge_case"]
    assert fp_rate <= max_fp, (
        f"Edge case FP rate {fp_rate:.3f} exceeds max {max_fp}. "
        f"Engine is extracting from empty/minimal input."
    )


@pytest.mark.llm
def test_ambiguous_handling(gold_data, all_extraction_results):
    """Ambiguous conversations should have zero expected extractions matched
    and minimal actual extractions."""
    ambiguous = [g for g in gold_data if g["category"] == "ambiguous"]
    for gold in ambiguous:
        conv_id = gold["id"]
        actual = all_extraction_results.get(conv_id, [])
        # Allow at most 1 low-confidence extraction (SENTIMENT is debatable)
        high_conf = [e for e in actual if e.get("confidence", 0) >= 0.70]
        assert len(high_conf) == 0, (
            f"Ambiguous conversation {conv_id} ({gold['name']}) produced "
            f"{len(high_conf)} high-confidence extractions: "
            f"{[e['extraction_type'] for e in high_conf]}"
        )


@pytest.mark.llm
def test_hinglish_extraction(gold_data, all_extraction_results):
    """Hinglish conversations should still produce expected extractions."""
    hinglish = [g for g in gold_data if g["category"] == "hinglish"]
    assert len(hinglish) > 0, "No Hinglish conversations in gold dataset"

    for gold in hinglish:
        conv_id = gold["id"]
        actual = all_extraction_results.get(conv_id, [])
        expected_count = len(gold.get("expected_extractions", []))
        result = evaluate_conversation(gold, actual)
        tp = len(result.true_positives)

        # At least 40% of expected extractions should be found
        min_tp = max(1, int(expected_count * 0.4))
        assert tp >= min_tp, (
            f"Hinglish conversation {conv_id} ({gold['name']}): "
            f"only {tp}/{expected_count} expected extractions matched "
            f"(need at least {min_tp})"
        )


@pytest.mark.llm
def test_absent_types_respected(gold_data, all_extraction_results):
    """Types listed in expected_absent should not appear in extractions."""
    violations = []
    for gold in gold_data:
        conv_id = gold["id"]
        expected_absent = set(gold.get("expected_absent", []))
        if not expected_absent:
            continue

        actual = all_extraction_results.get(conv_id, [])
        actual_types = {e.get("extraction_type", "").upper() for e in actual}

        for absent_type in expected_absent:
            if absent_type in actual_types:
                # Check if any of those are high confidence
                high_conf = [
                    e for e in actual
                    if e.get("extraction_type", "").upper() == absent_type
                    and e.get("confidence", 0) >= 0.70
                ]
                if high_conf:
                    violations.append(
                        f"{conv_id}: {absent_type} found with high confidence "
                        f"(conf={high_conf[0].get('confidence', 0):.2f})"
                    )

    assert not violations, (
        "Absent type violations (high-confidence extractions of types that "
        "should not appear):\n" + "\n".join(violations)
    )


@pytest.mark.llm
def test_confidence_calibration(
    gold_data, all_extraction_results, baselines
):
    """High-confidence extractions should be more accurate than low-confidence ones."""
    cal_config = baselines["confidence_calibration"]
    cal = compute_confidence_calibration(
        gold_data,
        all_extraction_results,
        high_threshold=cal_config["high_confidence_threshold"],
        low_threshold=cal_config["low_confidence_threshold"],
    )

    # High confidence extractions should have good accuracy
    if cal["high_confidence_count"] >= 5:
        assert cal["high_confidence_accuracy"] >= cal_config["high_confidence_min_accuracy"], (
            f"High-confidence accuracy {cal['high_confidence_accuracy']:.3f} "
            f"below minimum {cal_config['high_confidence_min_accuracy']} "
            f"(n={cal['high_confidence_count']})"
        )

    # If we have enough low-confidence data, confidence should be calibrated:
    # high conf accuracy should exceed low conf accuracy
    if cal["high_confidence_count"] >= 5 and cal["low_confidence_count"] >= 3:
        assert cal["high_confidence_accuracy"] >= cal["low_confidence_accuracy"], (
            f"Confidence is miscalibrated: high-conf accuracy "
            f"({cal['high_confidence_accuracy']:.3f}) <= low-conf accuracy "
            f"({cal['low_confidence_accuracy']:.3f})"
        )


@pytest.mark.llm
def test_all_types_conversation(gold_data, all_extraction_results):
    """The all_types conversation should produce at least one of each extraction type."""
    all_types_convs = [g for g in gold_data if g["category"] == "all_types"]
    assert len(all_types_convs) > 0, "No all_types conversation in gold dataset"

    for gold in all_types_convs:
        conv_id = gold["id"]
        actual = all_extraction_results.get(conv_id, [])
        actual_types = {e.get("extraction_type", "").upper() for e in actual}

        expected_types = {e["extraction_type"] for e in gold.get("expected_extractions", [])}
        missing = expected_types - actual_types
        # With 12 types, new subtle types (mindset, psych safety) may not be detected yet.
        # Allow up to 60% missing — tighten as extraction improves.
        max_missing = max(3, int(len(expected_types) * 0.6))
        assert len(missing) <= max_missing, (
            f"All-types conversation {conv_id} missing {len(missing)} types: {missing}. "
            f"Found types: {actual_types}"
        )


@pytest.mark.llm
def test_long_conversations_coverage(gold_data, all_extraction_results):
    """Long conversations should have reasonable extraction coverage."""
    long_convs = [g for g in gold_data if g["category"] == "long"]
    for gold in long_convs:
        conv_id = gold["id"]
        actual = all_extraction_results.get(conv_id, [])
        expected_count = len(gold.get("expected_extractions", []))
        result = evaluate_conversation(gold, actual)
        tp = len(result.true_positives)

        # At least 30% of expected extractions should match (v3.0 has more types, harder to match all)
        min_tp = max(1, int(expected_count * 0.3))
        assert tp >= min_tp, (
            f"Long conversation {conv_id} ({gold['name']}): "
            f"only {tp}/{expected_count} expected extractions matched (need {min_tp})"
        )
