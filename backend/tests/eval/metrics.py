"""Evaluation metrics for CIE extraction quality.

Computes precision, recall, F1 per extraction type, coverage,
false positive rate, and confidence calibration using fuzzy matching.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

from tests.eval.matching.keyword_matcher import KeywordMatcher, MatcherProtocol


@dataclass
class MatchResult:
    """Result of matching a single expected extraction against actual extractions."""
    expected: dict
    matched: bool = False
    matched_extraction: Optional[dict] = None
    keyword_match_ratio: float = 0.0


@dataclass
class ConversationEvalResult:
    """Evaluation result for a single conversation."""
    conversation_id: str
    true_positives: list[MatchResult] = field(default_factory=list)
    false_negatives: list[MatchResult] = field(default_factory=list)
    false_positives: list[dict] = field(default_factory=list)
    absent_type_violations: list[str] = field(default_factory=list)


@dataclass
class TypeMetrics:
    """Precision/recall/F1 for one extraction type."""
    extraction_type: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


@dataclass
class OverallMetrics:
    """Aggregated metrics across all conversations."""
    per_type: dict[str, TypeMetrics] = field(default_factory=dict)
    conversation_results: list[ConversationEvalResult] = field(default_factory=list)

    @property
    def total_tp(self) -> int:
        return sum(m.true_positives for m in self.per_type.values())

    @property
    def total_fp(self) -> int:
        return sum(m.false_positives for m in self.per_type.values())

    @property
    def total_fn(self) -> int:
        return sum(m.false_negatives for m in self.per_type.values())

    @property
    def overall_precision(self) -> float:
        denom = self.total_tp + self.total_fp
        return self.total_tp / denom if denom > 0 else 0.0

    @property
    def overall_recall(self) -> float:
        denom = self.total_tp + self.total_fn
        return self.total_tp / denom if denom > 0 else 0.0

    @property
    def overall_f1(self) -> float:
        p, r = self.overall_precision, self.overall_recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def evaluate_conversation(
    gold: dict,
    actual_extractions: list[dict],
    matcher: Optional[MatcherProtocol] = None,
) -> ConversationEvalResult:
    """Evaluate extraction results against gold standard for one conversation.

    Args:
        gold: Gold dataset entry with expected_extractions and expected_absent.
        actual_extractions: List of extraction dicts from the engine.
        matcher: Optional matcher implementing MatcherProtocol. Defaults to KeywordMatcher().

    Returns:
        ConversationEvalResult with TP/FP/FN details.
    """
    if matcher is None:
        matcher = KeywordMatcher()

    result = ConversationEvalResult(conversation_id=gold["id"])
    expected_list = gold.get("expected_extractions", [])
    expected_absent = set(gold.get("expected_absent", []))

    already_matched: set[int] = set()

    # Match each expected extraction against actuals
    for expected in expected_list:
        match = matcher.match(expected, actual_extractions, already_matched)
        if match is not None:
            idx, ratio = match
            already_matched.add(idx)
            result.true_positives.append(
                MatchResult(
                    expected=expected,
                    matched=True,
                    matched_extraction=actual_extractions[idx],
                    keyword_match_ratio=ratio,
                )
            )
        else:
            result.false_negatives.append(
                MatchResult(expected=expected, matched=False)
            )

    # Unmatched actuals are false positives
    for idx, actual in enumerate(actual_extractions):
        if idx not in already_matched:
            result.false_positives.append(actual)

    # Check expected_absent violations
    actual_types = {e.get("extraction_type", "").upper() for e in actual_extractions}
    for absent_type in expected_absent:
        if absent_type in actual_types:
            result.absent_type_violations.append(absent_type)

    return result


def compute_metrics(
    gold_dataset: list[dict],
    all_results: dict[str, list[dict]],
    matcher: Optional[MatcherProtocol] = None,
) -> OverallMetrics:
    """Compute aggregate metrics across all gold conversations.

    Args:
        gold_dataset: List of gold conversation entries.
        all_results: Dict mapping conversation ID to list of extraction dicts.
        matcher: Optional matcher implementing MatcherProtocol. Passed through
                 to evaluate_conversation. Defaults to KeywordMatcher().

    Returns:
        OverallMetrics with per-type and overall scores.
    """
    metrics = OverallMetrics()

    for gold in gold_dataset:
        conv_id = gold["id"]
        actual = all_results.get(conv_id, [])
        conv_result = evaluate_conversation(gold, actual, matcher=matcher)
        metrics.conversation_results.append(conv_result)

        # Aggregate per-type counts
        for tp in conv_result.true_positives:
            ext_type = tp.expected["extraction_type"]
            if ext_type not in metrics.per_type:
                metrics.per_type[ext_type] = TypeMetrics(extraction_type=ext_type)
            metrics.per_type[ext_type].true_positives += 1

        for fn in conv_result.false_negatives:
            ext_type = fn.expected["extraction_type"]
            if ext_type not in metrics.per_type:
                metrics.per_type[ext_type] = TypeMetrics(extraction_type=ext_type)
            metrics.per_type[ext_type].false_negatives += 1

        for fp in conv_result.false_positives:
            ext_type = fp.get("extraction_type", "UNKNOWN").upper()
            if ext_type not in metrics.per_type:
                metrics.per_type[ext_type] = TypeMetrics(extraction_type=ext_type)
            metrics.per_type[ext_type].false_positives += 1

    return metrics


def compute_false_positive_rate(
    gold_dataset: list[dict],
    all_results: dict[str, list[dict]],
    categories: list[str],
) -> float:
    """Compute false positive rate for conversations in specified categories.

    FP rate = conversations with any extraction / total conversations in category.
    Only considers conversations where expected_extractions is empty.
    """
    total = 0
    with_extractions = 0

    for gold in gold_dataset:
        if gold.get("category") not in categories:
            continue
        if gold.get("expected_extractions"):
            continue  # Skip conversations that should have extractions

        total += 1
        conv_id = gold["id"]
        actual = all_results.get(conv_id, [])
        if len(actual) > 0:
            with_extractions += 1

    return with_extractions / total if total > 0 else 0.0


def compute_confidence_calibration(
    gold_dataset: list[dict],
    all_results: dict[str, list[dict]],
    high_threshold: float = 0.85,
    low_threshold: float = 0.65,
) -> dict[str, float]:
    """Compute confidence calibration metrics.

    Checks if high-confidence extractions are more likely to be true positives
    than low-confidence ones.

    Returns dict with:
        - high_confidence_accuracy: fraction of high-conf extractions that are TPs
        - low_confidence_accuracy: fraction of low-conf extractions that are TPs
    """
    high_total = 0
    high_correct = 0
    low_total = 0
    low_correct = 0

    for gold in gold_dataset:
        conv_id = gold["id"]
        actual = all_results.get(conv_id, [])
        conv_result = evaluate_conversation(gold, actual)

        # Build set of matched actual indices
        matched_descriptions = set()
        for tp in conv_result.true_positives:
            if tp.matched_extraction:
                matched_descriptions.add(tp.matched_extraction.get("description", ""))

        for ext in actual:
            conf = ext.get("confidence", 0.0)
            is_tp = ext.get("description", "") in matched_descriptions

            if conf >= high_threshold:
                high_total += 1
                if is_tp:
                    high_correct += 1
            elif conf < low_threshold:
                low_total += 1
                if is_tp:
                    low_correct += 1

    return {
        "high_confidence_accuracy": high_correct / high_total if high_total > 0 else 0.0,
        "low_confidence_accuracy": low_correct / low_total if low_total > 0 else 0.0,
        "high_confidence_count": high_total,
        "low_confidence_count": low_total,
    }


def compute_stability_metrics(
    runs: list[list[dict]],
) -> dict[str, float]:
    """Compute stability metrics across multiple runs of the same conversation.

    Args:
        runs: List of extraction results from multiple runs of the same conversation.

    Returns:
        Dict with type_consistency, count_variance, confidence_std.
    """
    if not runs:
        return {"type_consistency": 0.0, "count_variance": 0.0, "confidence_std": 0.0}

    # Type consistency: fraction of runs that produce the same set of types
    type_sets = [frozenset(e.get("extraction_type", "") for e in run) for run in runs]
    if type_sets:
        most_common = max(set(type_sets), key=type_sets.count)
        type_consistency = type_sets.count(most_common) / len(type_sets)
    else:
        type_consistency = 1.0

    # Count variance: coefficient of variation of extraction counts
    counts = [len(run) for run in runs]
    mean_count = sum(counts) / len(counts) if counts else 0
    if mean_count > 0:
        variance = sum((c - mean_count) ** 2 for c in counts) / len(counts)
        count_cv = math.sqrt(variance) / mean_count
    else:
        count_cv = 0.0

    # Confidence std: average standard deviation of confidence per extraction type
    type_confidences: dict[str, list[list[float]]] = defaultdict(list)
    for run in runs:
        per_type: dict[str, list[float]] = defaultdict(list)
        for ext in run:
            per_type[ext.get("extraction_type", "")].append(ext.get("confidence", 0.0))
        for ext_type, confs in per_type.items():
            type_confidences[ext_type].append(confs)

    stds = []
    for ext_type, run_confs_list in type_confidences.items():
        # Collect all confidences across runs for this type
        all_confs = [c for run_confs in run_confs_list for c in run_confs]
        if len(all_confs) > 1:
            mean_c = sum(all_confs) / len(all_confs)
            var_c = sum((c - mean_c) ** 2 for c in all_confs) / len(all_confs)
            stds.append(math.sqrt(var_c))

    avg_confidence_std = sum(stds) / len(stds) if stds else 0.0

    return {
        "type_consistency": type_consistency,
        "count_variance": count_cv,
        "confidence_std": avg_confidence_std,
    }


def format_report(metrics: OverallMetrics) -> str:
    """Format metrics as a human-readable report string."""
    lines = [
        "=" * 60,
        "CIE Extraction Evaluation Report",
        "=" * 60,
        "",
        f"Overall Precision: {metrics.overall_precision:.3f}",
        f"Overall Recall:    {metrics.overall_recall:.3f}",
        f"Overall F1:        {metrics.overall_f1:.3f}",
        "",
        f"Total TP: {metrics.total_tp}  FP: {metrics.total_fp}  FN: {metrics.total_fn}",
        "",
        "Per-Type Breakdown:",
        "-" * 50,
    ]

    for ext_type in sorted(metrics.per_type.keys()):
        tm = metrics.per_type[ext_type]
        lines.append(
            f"  {ext_type:15s}  P={tm.precision:.2f}  R={tm.recall:.2f}  "
            f"F1={tm.f1:.2f}  (TP={tm.true_positives} FP={tm.false_positives} FN={tm.false_negatives})"
        )

    lines.append("")
    lines.append("Per-Conversation Summary:")
    lines.append("-" * 50)
    for cr in metrics.conversation_results:
        tp = len(cr.true_positives)
        fn = len(cr.false_negatives)
        fp = len(cr.false_positives)
        violations = cr.absent_type_violations
        violation_str = f"  VIOLATIONS: {violations}" if violations else ""
        lines.append(f"  {cr.conversation_id:12s}  TP={tp} FN={fn} FP={fp}{violation_str}")

    lines.append("=" * 60)
    return "\n".join(lines)
