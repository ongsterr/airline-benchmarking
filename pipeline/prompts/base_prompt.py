"""Assemble EPD-style prompt sections into a single system prompt."""

from __future__ import annotations

_SECTION_ORDER = (
    "role",
    "context",
    "instructions",
    "field_definitions",
    "search_patterns",
    "constraints",
    "output_format",
    "example",
)


def generate_prompt(sections: dict[str, str]) -> str:
    """Concatenate named sections in a fixed order with markdown headings."""
    parts: list[str] = []
    for key in _SECTION_ORDER:
        content = sections.get(key, "").strip()
        if not content:
            continue
        title = key.replace("_", " ").title()
        parts.append(f"## {title}\n\n{content}")
    return "\n\n".join(parts)
