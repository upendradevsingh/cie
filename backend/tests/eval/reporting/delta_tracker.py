"""Delta tracker — persists eval run metrics for trend comparison.

Stores the last 50 runs in a JSON file so that reports can show
deltas vs. the previous run.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "run_history.json")


def save_run(metrics_dict: dict) -> None:
    """Save eval run metrics to history.

    Args:
        metrics_dict: Flat dict of metric values (overall_f1, overall_precision, etc.).
    """
    history = load_history()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics_dict,
    }
    history.append(entry)
    # Keep last 50 runs
    history = history[-50:]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def load_history() -> list[dict]:
    """Load run history from disk.

    Returns:
        List of run entries, each with timestamp and metrics dict.
    """
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []


def get_previous_metrics() -> dict:
    """Get metrics from the most recent previous run.

    Returns:
        Metrics dict from the last saved run, or empty dict if no history.
    """
    history = load_history()
    if len(history) >= 1:
        return history[-1].get("metrics", {})
    return {}
