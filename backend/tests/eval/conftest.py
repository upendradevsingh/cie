"""Fixtures for CIE evaluation tests."""
import json
from pathlib import Path
from typing import Any

import pytest

from app.profiles import ProfileLoader, ExtractionProfile

EVAL_DIR = Path(__file__).parent
PROFILES_DIR = str(Path(__file__).parent.parent.parent / "app" / "profiles")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register --match-mode CLI option for eval tests."""
    parser.addoption(
        "--match-mode",
        action="store",
        default="keyword",
        choices=("keyword", "embedding", "hybrid"),
        help="Matching strategy for eval: keyword (default), embedding, or hybrid.",
    )


@pytest.fixture(scope="session")
def match_mode(request: pytest.FixtureRequest) -> str:
    """Return the --match-mode value chosen at invocation time."""
    return request.config.getoption("--match-mode")


@pytest.fixture(scope="session")
def gold_dataset() -> list[dict[str, Any]]:
    """Load the gold annotated dataset."""
    dataset_path = EVAL_DIR / "gold_dataset.json"
    with open(dataset_path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def baseline_scores() -> dict[str, Any]:
    """Load baseline score thresholds."""
    scores_path = EVAL_DIR / "baseline_scores.json"
    with open(scores_path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def performance_profile() -> ExtractionProfile:
    """Load the performance extraction profile."""
    loader = ProfileLoader(PROFILES_DIR)
    return loader.load("performance")


@pytest.fixture(scope="session")
def profile_loader() -> ProfileLoader:
    """Return a ProfileLoader pointed at the real profiles directory."""
    return ProfileLoader(PROFILES_DIR)


def build_transcript_from_segments(segments: list[dict]) -> str:
    """Convert gold dataset segments into the transcript format the engine expects."""
    lines = []
    for seg in segments:
        speaker = seg.get("speaker", "Unknown")
        text = seg.get("text", "").strip()
        if text:
            lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def gold_conversations_by_category(
    gold_dataset: list[dict], category: str
) -> list[dict]:
    """Filter gold dataset by category."""
    return [g for g in gold_dataset if g.get("category") == category]


def gold_conversations_by_tag(
    gold_dataset: list[dict], tag: str
) -> list[dict]:
    """Filter gold dataset by tag."""
    return [g for g in gold_dataset if tag in g.get("tags", [])]
