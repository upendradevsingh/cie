"""Manage disagreement queue for human adjudication.

Reads gold entries with adjudicated_items, formats them for human review.
"""
import json
import sys


def format_adjudication_queue(gold_entries: list[dict]) -> str:
    """Format adjudication items for human review."""
    lines = ["━━━ Adjudication Queue ━━━", ""]

    for entry in gold_entries:
        items = entry.get("adjudicated_items", [])
        if not items:
            continue
        lines.append(f"Conversation: {entry['id']} — {entry.get('name', '')}")
        for item in items:
            lines.append(f"  Type: {item['extraction_type']}")
            lines.append(f"  Agreement: {item.get('agreement', '?')}")
            descs = item.get("model_descriptions", {})
            for model, desc in descs.items():
                lines.append(f"    {model}: {desc}")
            lines.append(f"  → Accept / Reject / Edit?")
            lines.append("")

    if len(lines) == 2:
        lines.append("No items need adjudication.")

    return "\n".join(lines)


def main():
    """Read gold dataset and show adjudication queue."""
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    entries = data if isinstance(data, list) else [data]
    print(format_adjudication_queue(entries))


if __name__ == "__main__":
    main()
