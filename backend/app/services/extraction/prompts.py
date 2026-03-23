"""Dynamic prompt builder from profile configuration."""
import json
import logging
from typing import Any

from app.profiles import ExtractionProfile

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert conversation analyst. Your task is to extract structured intelligence from a conversation transcript based on the profile configuration provided.

Rules:
1. Only extract items you are confident about (confidence >= threshold)
2. Return valid JSON only — no prose, no markdown
3. Assign confidence scores between 0.0 and 1.0
4. If nothing qualifies for an extraction type, return an empty list for that type
5. Evidence should be a direct quote from the transcript
"""

EXTRACTION_PROMPT_TEMPLATE = """# Profile: {profile_name}
{meeting_context}
## Participants
{participants_json}

## Extraction Types to Identify

{extraction_sections}

## Transcript
{transcript}

## Response Format
Return a JSON object with this exact structure:
{{
  "extractions": [
    {{
      "extraction_type": "<TYPE>",
      "description": "<clear description of what was extracted>",
      "confidence": <0.0-1.0>,
      "attributed_to": {{"externalId": "<id>", "name": "<name>", "role": "<role>"}} or null,
      "evidence": "<direct quote from transcript>",
      "attributes": {{<profile-specific attributes for this type>}}
    }}
  ],
  "summary": "<{summary_style} summary in {summary_max_length} words or less>"
}}

Important: Return ONLY the JSON object. No prose before or after."""


def build_extraction_prompt(
    profile: ExtractionProfile,
    transcript: str,
    participants: list[dict[str, Any]],
    meeting_type: str | None = None,
    correction_examples: dict[str, str] | None = None,
) -> str:
    """Build a dynamic extraction prompt from a profile configuration (all types)."""
    return build_extraction_prompt_for_types(
        profile, transcript, participants, meeting_type=meeting_type,
        correction_examples=correction_examples,
    )


def build_extraction_prompt_for_types(
    profile: ExtractionProfile,
    transcript: str,
    participants: list[dict[str, Any]],
    type_filter: set[str] | None = None,
    meeting_type: str | None = None,
    correction_examples: dict[str, str] | None = None,
) -> str:
    """Build a dynamic extraction prompt, optionally filtered to specific types.

    Args:
        profile: The extraction profile to use.
        transcript: Conversation transcript text.
        participants: List of participant dicts.
        type_filter: If provided, only include extraction types in this set.
                     If None, include all enabled types.
        meeting_type: Optional meeting type for context-aware extraction.
        correction_examples: Optional dict of extraction_type -> few-shot correction text.
    """
    sections = []
    for ext_type, config in profile.enabled_types().items():
        if type_filter is not None and ext_type not in type_filter:
            continue
        attr_descriptions = []
        for attr in config.attributes:
            desc = f"  - {attr.name} ({attr.type}"
            if attr.values:
                desc += f", options: {attr.values}"
            if attr.min is not None or attr.max is not None:
                desc += f", range: {attr.min}-{attr.max}"
            if attr.required:
                desc += ", required"
            desc += ")"
            attr_descriptions.append(desc)

        section = f"""### {ext_type}
Description: {config.description}
Confidence threshold: {config.confidence_threshold} (only extract if confidence >= {config.confidence_threshold})"""

        if config.prompt_hint:
            section += f"\nHint: {config.prompt_hint}"

        if attr_descriptions:
            section += f"\nAttributes:\n" + "\n".join(attr_descriptions)

        # Append few-shot correction examples if available for this type
        if correction_examples and ext_type in correction_examples:
            section += f"\n\n{correction_examples[ext_type]}"

        sections.append(section)

    summary_style = "concise"
    summary_max_length = 200
    if profile.summary:
        summary_style = profile.summary.style
        summary_max_length = profile.summary.max_length

    from app.services.extraction.meeting_types import get_meeting_config
    config = get_meeting_config(meeting_type)
    meeting_context = "\n" + config.extraction_preamble if config.extraction_preamble else ""

    return EXTRACTION_PROMPT_TEMPLATE.format(
        profile_name=profile.display_name,
        meeting_context=meeting_context,
        participants_json=json.dumps(participants, indent=2),
        extraction_sections="\n\n".join(sections),
        transcript=transcript,
        summary_style=summary_style,
        summary_max_length=summary_max_length,
    )
