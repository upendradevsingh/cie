"""Diagnostic eval report generator.

Takes an OverallMetrics object and produces a structured report with
per-type breakdowns, worst misses, confusion patterns, and recommendations.
"""
from __future__ import annotations

from tests.eval.metrics import OverallMetrics

CONTENT_TYPES = {
    "COMMITMENT",
    "BLOCKER",
    "ACTION_ITEM",
    "DECISION",
    "GOAL_UPDATE",
    "RECOGNITION",
}
BEHAVIORAL_TYPES = {
    "FEEDBACK",
    "COACHING_MOMENT",
    "PSYCHOLOGICAL_SAFETY",
    "MINDSET_SIGNAL",
    "ACCOUNTABILITY_SIGNAL",
    "SENTIMENT",
}


def status_indicator(f1: float) -> str:
    """Return a visual indicator based on F1 score."""
    if f1 >= 0.60:
        return "\u2705"
    if f1 >= 0.30:
        return "\u26a0\ufe0f"
    return "\U0001f527"


def generate_report(
    metrics: OverallMetrics,
    previous_metrics: dict | None = None,
    annotation_stats: dict | None = None,
) -> str:
    """Generate diagnostic eval report.

    Args:
        metrics: Current run's OverallMetrics.
        previous_metrics: Optional dict from a previous run for delta display.
        annotation_stats: Optional dict mapping annotation method to conversation count.

    Returns:
        Formatted multi-line report string.
    """
    lines: list[str] = []
    lines.append("\u2501\u2501\u2501 CIE Eval Report \u2501\u2501\u2501")
    lines.append("")

    # --- Overall with deltas ---
    f1 = metrics.overall_f1
    p = metrics.overall_precision
    r = metrics.overall_recall
    delta_str = ""
    if previous_metrics:
        prev_f1 = previous_metrics.get("overall_f1", 0)
        diff = f1 - prev_f1
        arrow = "\u2191" if diff >= 0 else "\u2193"
        delta_str = f" ({arrow}{abs(diff):.3f})"
    lines.append(f"OVERALL: F1={f1:.3f}{delta_str}  P={p:.3f}  R={r:.3f}")
    lines.append(f"Total TP={metrics.total_tp}  FP={metrics.total_fp}  FN={metrics.total_fn}")
    lines.append("")

    # --- Per-type split by content/behavioral ---
    section_labels = [
        ("CONTENT EXTRACTION (Pass 1)", CONTENT_TYPES),
        ("BEHAVIORAL EXTRACTION (Pass 2)", BEHAVIORAL_TYPES),
    ]
    for label, type_set in section_labels:
        lines.append(f"\u2500\u2500\u2500 {label} \u2500\u2500\u2500")
        for ext_type in sorted(type_set):
            if ext_type in metrics.per_type:
                tm = metrics.per_type[ext_type]
                ind = status_indicator(tm.f1)
                lines.append(
                    f"  {ind} {ext_type:25s} P={tm.precision:.2f}  R={tm.recall:.2f}  "
                    f"F1={tm.f1:.2f}  (TP={tm.true_positives} FP={tm.false_positives} FN={tm.false_negatives})"
                )
            else:
                lines.append(f"  \U0001f527 {ext_type:25s} (no data)")
        lines.append("")

    # --- Worst misses (top 5 false negatives) ---
    lines.append("\u2500\u2500\u2500 WORST MISSES \u2500\u2500\u2500")
    all_fn: list[str] = []
    for cr in metrics.conversation_results:
        for fn in cr.false_negatives:
            kw = fn.expected.get("description_contains", [])
            all_fn.append(
                f"  {cr.conversation_id}: missed {fn.expected['extraction_type']} "
                f'"{" ".join(kw)}"'
            )
    for miss in all_fn[:5]:
        lines.append(miss)
    if not all_fn:
        lines.append("  No false negatives detected")
    lines.append("")

    # --- Confusion patterns ---
    lines.append("\u2500\u2500\u2500 CONFUSION PATTERNS \u2500\u2500\u2500")
    confusion: dict[str, int] = {}
    for cr in metrics.conversation_results:
        fn_types = {fn.expected["extraction_type"] for fn in cr.false_negatives}
        fp_types = {fp.get("extraction_type", "").upper() for fp in cr.false_positives}
        for fn_t in fn_types:
            for fp_t in fp_types:
                if fn_t != fp_t:
                    key = f"{fp_t} confused with {fn_t}"
                    confusion[key] = confusion.get(key, 0) + 1
    for pattern, count in sorted(confusion.items(), key=lambda x: -x[1])[:5]:
        lines.append(f"  {pattern}: {count} cases")
    if not confusion:
        lines.append("  No confusion patterns detected")
    lines.append("")

    # --- Annotation coverage ---
    if annotation_stats:
        lines.append("\u2500\u2500\u2500 ANNOTATION COVERAGE \u2500\u2500\u2500")
        for method, count in annotation_stats.items():
            lines.append(f"  {method}: {count} conversations")
        lines.append("")

    # --- Auto-recommendations ---
    lines.append("\u2500\u2500\u2500 RECOMMENDATIONS \u2500\u2500\u2500")
    has_recommendations = False
    for ext_type, tm in sorted(metrics.per_type.items(), key=lambda x: x[1].f1):
        if tm.f1 < 0.30 and (tm.true_positives + tm.false_negatives) > 0:
            lines.append(
                f"  \u2192 Improve {ext_type} prompt (F1={tm.f1:.2f}, recall={tm.recall:.2f})"
            )
            has_recommendations = True
        elif tm.false_positives > tm.true_positives and tm.true_positives > 0:
            lines.append(
                f"  \u2192 Reduce {ext_type} false positives "
                f"(FP={tm.false_positives} > TP={tm.true_positives})"
            )
            has_recommendations = True
    if not has_recommendations:
        lines.append("  No immediate recommendations")
    lines.append("")

    return "\n".join(lines)
