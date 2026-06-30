"""Generate EPD-style output skeleton for flight features research."""

from __future__ import annotations

_CABIN_KEYS = ("first", "business", "premium_economy", "economy")

_FEATURE_FIELDS = (
    ('"check-in_priority": "<string Yes/No>|null"'),
    ('"cabin_bag_pieces": <integer>|null'),
    ('"cabin_bag_kg_per_piece": <integer>|null'),
    ('"cabin_bag_kg_total": <integer>|null'),
    ('"checked_bag_pieces": <integer>|null'),
    ('"checked_bag_kg_per_piece": <integer>|null'),
    ('"checked_bag_kg_total": <integer>|null'),
    ('"boarding_priority": "<string Yes/No>|null"'),
    ('"lounge_access": "<string Yes/No>|null"'),
    ('"amenity_kit": ["<string>", ...]|null'),
    ('"amenity_kit_brand": "<string>|null"'),
)


def build_flight_research_output_format() -> str:
    lines = [
        "Return the output in JSON format in this exact structure without any other text or comments:",
        "{",
    ]
    for index, key in enumerate(_CABIN_KEYS):
        comma = "," if index < len(_CABIN_KEYS) - 1 else ""
        lines.append(f'  "{key}": {{')
        lines.append('    "cabin_class": "<string>",')
        lines.append('    "sources": [')
        lines.append('      {')
        lines.append('        "url": "<https://...>",')
        lines.append('        "title": "<page title>",')
        lines.append('        "publisher": "<domain or publisher name>"')
        lines.append("      }")
        lines.append("    ],")
        lines.append('    "features": {')
        for feat_index, field in enumerate(_FEATURE_FIELDS):
            feat_comma = "," if feat_index < len(_FEATURE_FIELDS) - 1 else ""
            lines.append(f"      {field}{feat_comma}")
        lines.append("    }")
        lines.append(f"  }}{comma}")
    lines.append("}")
    return "\n".join(lines)


def build_flight_output_format() -> str:
    """Legacy flat cabins wrapper — kept for backward compatibility in tests."""
    return build_flight_research_output_format()
