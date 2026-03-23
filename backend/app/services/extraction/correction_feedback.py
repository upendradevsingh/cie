"""Few-shot correction feedback for extraction improvement.

Queries past corrections and formats them as prompt examples so the LLM
learns from prior mistakes. Uses hierarchical scoping:
  1. Tenant-specific corrections first (most relevant)
  2. Profile-wide corrections as fallback (anonymized, cross-tenant learning)
"""
import logging
import uuid
from collections import defaultdict

from sqlalchemy import and_, not_
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.correction import Correction
from app.models.extraction import Extraction

logger = logging.getLogger(__name__)

MAX_EXAMPLES_PER_TYPE = 3


def get_correction_examples(
    db: Session,
    tenant_id: uuid.UUID,
    profile_id: str,
    extraction_types: set[str],
) -> dict[str, str]:
    """Query corrections and format as few-shot prompt examples.

    Returns a dict mapping extraction_type -> formatted prompt text.
    Only includes types that have corrections. Returns empty dict if
    no corrections exist.
    """
    if not extraction_types:
        return {}

    # Step 1: Tenant-specific corrections
    tenant_corrections = _query_corrections(
        db, extraction_types, profile_id, tenant_id=tenant_id,
    )

    # Step 2: Profile-wide fallback for types that need more examples
    types_needing_more = {
        t for t in extraction_types
        if len(tenant_corrections.get(t, [])) < MAX_EXAMPLES_PER_TYPE
    }

    profile_corrections: dict[str, list] = {}
    if types_needing_more:
        profile_corrections = _query_corrections(
            db, types_needing_more, profile_id,
            exclude_tenant_id=tenant_id,
        )

    # Merge: tenant-first, then profile-wide up to cap
    merged = _merge_corrections(tenant_corrections, profile_corrections)

    if not merged:
        return {}

    # Format as prompt text
    result = {}
    total = 0
    for ext_type, examples in merged.items():
        result[ext_type] = _format_examples(ext_type, examples)
        total += len(examples)

    logger.info(
        "Correction feedback: tenant=%s profile=%s types_with_corrections=%d total_examples=%d",
        tenant_id, profile_id, len(result), total,
    )
    return result


def _query_corrections(
    db: Session,
    extraction_types: set[str],
    profile_id: str,
    tenant_id: uuid.UUID | None = None,
    exclude_tenant_id: uuid.UUID | None = None,
) -> dict[str, list]:
    """Query corrections from DB, grouped by extraction type."""
    query = (
        db.query(Correction, Extraction)
        .join(Extraction, Correction.extraction_id == Extraction.id)
        .join(Conversation, Extraction.conversation_id == Conversation.id)
        .filter(
            Extraction.extraction_type.in_(extraction_types),
            Conversation.profile_id == profile_id,
            Correction.correction_type.in_(["modify", "reject"]),
        )
        .order_by(Correction.created_at.desc())
    )

    if tenant_id is not None:
        query = query.filter(Extraction.tenant_id == tenant_id)

    if exclude_tenant_id is not None:
        query = query.filter(Extraction.tenant_id != exclude_tenant_id)

    # Fetch more than we need, then cap per type in Python
    # (per-group LIMIT is complex in SQLAlchemy)
    rows = query.limit(MAX_EXAMPLES_PER_TYPE * len(extraction_types)).all()

    grouped: dict[str, list] = defaultdict(list)
    for correction, extraction in rows:
        ext_type = extraction.extraction_type
        if len(grouped[ext_type]) < MAX_EXAMPLES_PER_TYPE:
            grouped[ext_type].append({
                "correction": correction,
                "extraction": extraction,
                "is_cross_tenant": tenant_id is None or extraction.tenant_id != tenant_id,
            })

    return dict(grouped)


def _merge_corrections(
    tenant: dict[str, list],
    profile: dict[str, list],
) -> dict[str, list]:
    """Merge tenant and profile corrections, capping at MAX_EXAMPLES_PER_TYPE."""
    merged: dict[str, list] = {}

    all_types = set(tenant.keys()) | set(profile.keys())
    for ext_type in all_types:
        examples = list(tenant.get(ext_type, []))
        remaining = MAX_EXAMPLES_PER_TYPE - len(examples)
        if remaining > 0 and ext_type in profile:
            for ex in profile[ext_type][:remaining]:
                ex["is_cross_tenant"] = True
                examples.append(ex)
        if examples:
            merged[ext_type] = examples

    return merged


def _format_examples(ext_type: str, examples: list[dict]) -> str:
    """Format correction examples as prompt text for a single extraction type."""
    lines = [f"#### Prior corrections for {ext_type} (learn from these mistakes):"]

    for ex in examples:
        correction: Correction = ex["correction"]
        extraction: Extraction = ex["extraction"]
        is_cross_tenant: bool = ex["is_cross_tenant"]

        # Anonymize cross-tenant examples
        desc = extraction.description
        if is_cross_tenant and extraction.attributed_to:
            desc = desc.replace(
                extraction.attributed_to.get("name", ""), "a team member"
            )

        if correction.correction_type == "reject":
            lines.append(
                f"- ORIGINAL: \"{desc}\" (confidence: {extraction.confidence})\n"
                f"  REJECTED: This extraction was incorrect and should not have been created."
            )
        else:
            lines.append(
                f"- ORIGINAL: \"{desc}\" (confidence: {extraction.confidence})\n"
                f"  CORRECTED FIELD: {correction.field_name} → \"{correction.corrected_value}\""
            )

        if correction.correction_note:
            lines.append(f"  REVIEWER NOTE: \"{correction.correction_note}\"")

    return "\n".join(lines)
