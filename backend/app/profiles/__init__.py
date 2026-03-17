"""Profile loading system for CIE.

Profiles are YAML files defining extraction schema per domain.
ProfileLoader reads YAML files and returns ExtractionProfile objects.
"""
import logging
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ProfileAttribute(BaseModel):
    name: str
    type: str
    required: bool = False
    values: Optional[list[str]] = None
    min: Optional[float] = None
    max: Optional[float] = None


class ExtractionTypeConfig(BaseModel):
    enabled: bool = True
    confidence_threshold: float = 0.75
    description: str = ""
    prompt_hint: Optional[str] = None
    attributes: list[ProfileAttribute] = []


class ProfileLLM(BaseModel):
    model: str = "gpt-4o"
    temperature: float = 0.15
    max_tokens: int = 2048
    fallback_model: Optional[str] = None


class ProfileSummary(BaseModel):
    enabled: bool = True
    max_length: int = 200
    style: str = "concise"


class ExtractionProfile(BaseModel):
    profile_id: str
    version: str = "1.0"
    display_name: str
    description: str = ""
    llm: ProfileLLM = ProfileLLM()
    extraction_types: dict[str, ExtractionTypeConfig] = {}
    summary: Optional[ProfileSummary] = None

    def get_threshold(self, extraction_type: str) -> float:
        config = self.extraction_types.get(extraction_type)
        return config.confidence_threshold if config else 0.75

    def enabled_types(self) -> dict[str, ExtractionTypeConfig]:
        return {k: v for k, v in self.extraction_types.items() if v.enabled}


class ProfileLoader:
    """Loads and caches YAML profiles from the profiles directory."""

    def __init__(self, profiles_dir: Optional[str] = None):
        if profiles_dir is None:
            from app.config import settings
            profiles_dir = settings.PROFILES_DIR
        self._dir = Path(profiles_dir)
        self._cache: dict[str, ExtractionProfile] = {}

    def load(self, profile_id: str) -> ExtractionProfile:
        """Load a profile by ID. Cached after first load."""
        if profile_id in self._cache:
            return self._cache[profile_id]

        yaml_path = self._dir / f"{profile_id}.yaml"
        if not yaml_path.exists():
            raise ValueError(f"Profile '{profile_id}' not found at {yaml_path}")

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        profile = ExtractionProfile.model_validate(data)
        self._cache[profile_id] = profile
        logger.info("Loaded profile: %s v%s", profile_id, profile.version)
        return profile

    def list_profiles(self) -> list[str]:
        """List available profile IDs from YAML files."""
        return [p.stem for p in self._dir.glob("*.yaml")]

    def get_all(self) -> list[ExtractionProfile]:
        """Load and return all available profiles."""
        profiles = []
        for profile_id in self.list_profiles():
            try:
                profiles.append(self.load(profile_id))
            except Exception as e:
                logger.warning("Failed to load profile %s: %s", profile_id, e)
        return profiles


# Module-level loader instance
_loader: Optional[ProfileLoader] = None


def get_profile_loader() -> ProfileLoader:
    global _loader
    if _loader is None:
        _loader = ProfileLoader()
    return _loader
