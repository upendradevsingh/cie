"""Tests for the profile loading system."""
import pytest
from pathlib import Path

from app.profiles import ProfileLoader, ExtractionProfile


PROFILES_DIR = str(Path(__file__).parent.parent / "app" / "profiles")


def test_load_performance_profile():
    loader = ProfileLoader(PROFILES_DIR)
    profile = loader.load("performance")
    assert profile.profile_id == "performance"
    assert profile.display_name == "Performance Management"
    assert "COMMITMENT" in profile.extraction_types
    assert "BLOCKER" in profile.extraction_types
    assert "FEEDBACK" in profile.extraction_types
    assert "SENTIMENT" in profile.extraction_types
    assert profile.llm.model == "gpt-4o-mini"


def test_load_sales_profile():
    loader = ProfileLoader(PROFILES_DIR)
    profile = loader.load("sales")
    assert profile.profile_id == "sales"
    assert "QUALITY_SCORE" in profile.extraction_types
    assert "INTENT_SIGNAL" in profile.extraction_types
    assert "LEAD_INTENT" in profile.extraction_types


def test_list_profiles():
    loader = ProfileLoader(PROFILES_DIR)
    profiles = loader.list_profiles()
    assert "performance" in profiles
    assert "sales" in profiles


def test_profile_caching():
    loader = ProfileLoader(PROFILES_DIR)
    p1 = loader.load("performance")
    p2 = loader.load("performance")
    assert p1 is p2  # Same object from cache


def test_unknown_profile_raises():
    loader = ProfileLoader(PROFILES_DIR)
    with pytest.raises(ValueError, match="not found"):
        loader.load("nonexistent_profile")


def test_get_threshold():
    loader = ProfileLoader(PROFILES_DIR)
    profile = loader.load("performance")
    # COMMITMENT has threshold 0.80
    assert profile.get_threshold("COMMITMENT") == 0.80
    # Unknown type returns default 0.75
    assert profile.get_threshold("UNKNOWN_TYPE") == 0.75


def test_enabled_types_filters_disabled():
    loader = ProfileLoader(PROFILES_DIR)
    profile = loader.load("performance")
    enabled = profile.enabled_types()
    # All types in performance profile are enabled by default
    assert len(enabled) > 0
    for config in enabled.values():
        assert config.enabled is True


def test_performance_commitment_attributes():
    loader = ProfileLoader(PROFILES_DIR)
    profile = loader.load("performance")
    commitment = profile.extraction_types["COMMITMENT"]
    attr_names = [a.name for a in commitment.attributes]
    assert "deadline" in attr_names
    assert "specificity" in attr_names
