"""Prompt for bulk enrichment of Emirates menu items."""

from __future__ import annotations

from typing import Any

from pipeline.prompts.base_prompt import generate_prompt

MENU_ENRICHMENT_PROMPT_VERSION = "menu_enrichment_prompt_v1"
MENU_ENRICHMENT_VERSION = "menu_enrichment_v1"

_EXAMPLE_JSON = """{
  "items": [
    {
      "item_hash": "m:76246",
      "code": "76246",
      "item_type": "food",
      "beverage_type": null,
      "is_vegetarian": true,
      "is_vegan": true,
      "is_localized": false,
      "localization_confidence": 0.9,
      "localization_note": "Western vegan dish; not specifically tied to the non-DXB endpoint"
    },
    {
      "item_hash": "m:80857",
      "code": "80857",
      "item_type": "food",
      "beverage_type": null,
      "is_vegetarian": false,
      "is_vegan": false,
      "is_localized": true,
      "localization_confidence": 0.92,
      "localization_note": "Bengali-style mutton khichuri matches DAC/Bangladesh cuisine"
    },
    {
      "item_hash": "m:BV000021",
      "code": "BV000021",
      "item_type": "beverage",
      "beverage_type": "non_alcoholic",
      "is_vegetarian": null,
      "is_vegan": null,
      "is_localized": null,
      "localization_confidence": null,
      "localization_note": null
    },
    {
      "item_hash": "m:BV000037",
      "code": "BV000037",
      "item_type": "beverage",
      "beverage_type": "alcoholic",
      "is_vegetarian": null,
      "is_vegan": null,
      "is_localized": null,
      "localization_confidence": null,
      "localization_note": null
    }
  ]
}"""


def _escape_cell(value: str | None) -> str:
    text = (value or "").replace("|", "\\|").replace("\n", " ").strip()
    return text or ""


def build_items_markdown_table(items: list[dict[str, Any]]) -> str:
    lines = [
        "| item_hash | code | category | subcategory | title | desc |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in items:
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_cell(str(item.get("item_hash") or "")),
                    _escape_cell(str(item.get("code") or "")),
                    _escape_cell(str(item.get("category") or "")),
                    _escape_cell(str(item.get("subcategory") or "")),
                    _escape_cell(str(item.get("title") or "")),
                    _escape_cell(str(item.get("desc") or "")),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def build_menu_enrichment_prompt(
    items: list[dict[str, Any]],
    *,
    origin_iata: str,
    dest_iata: str,
    localization_target: str | None,
    cabin_norm: str | None = None,
) -> tuple[str, str]:
    """Build system + human messages for bulk menu enrichment."""
    target_note = (
        f"Localization target (non-DXB endpoint): {localization_target}."
        if localization_target
        else "No non-DXB endpoint (both ends are DXB or unknown); is_localized should be false for food."
    )
    system_prompt = generate_prompt(
        {
            "role": (
                "You enrich Emirates onboard menu items for flight benchmarking. "
                "Classify each item and return structured enrichment fields only."
            ),
            "context": (
                f"Route: {origin_iata} → {dest_iata}. "
                f"Cabin: {cabin_norm or 'unknown'}. "
                f"{target_note} "
                "Use only the provided title and description (plus category/subcategory as context). "
                "Do not invent ingredients."
            ),
            "instructions": (
                "For every row in the markdown table, return one enrichment object.\n"
                "- item_type must be food or beverage.\n"
                "- Prefer category/subcategory cues (e.g. Beverages, Wine, Mocktails, Main Course) "
                "and BV* codes for beverages; Fresh Juice under Breakfast is usually beverage.\n"
                "- beverage → beverage_type alcoholic|non_alcoholic; set food-only fields to null.\n"
                "- food → is_vegetarian and is_vegan booleans; beverage_type null; "
                "set is_localized, localization_confidence (0–1), localization_note.\n"
                "- vegan implies vegetarian=true.\n"
                "- Meat/fish/chicken/mutton/seafood in title or serving sides ⇒ not vegetarian/vegan.\n"
                "- is_localized=true ONLY when title/description identify cuisine specifically "
                "associated with the non-DXB localization target country/region. "
                "Generic, UAE, Middle Eastern, or globally common dishes are false unless "
                "specifically tied to that target.\n"
                "- localization_note must briefly cite title/description evidence.\n"
                "- Return every item_hash+code exactly once; do not invent new codes."
            ),
            "field_definitions": (
                "items: array of enrichment objects.\n"
                "item_hash / code: must match input.\n"
                "item_type: food|beverage.\n"
                "beverage_type: alcoholic|non_alcoholic|null.\n"
                "is_vegetarian / is_vegan: boolean|null.\n"
                "is_localized: boolean|null.\n"
                "localization_confidence: number 0–1|null.\n"
                "localization_note: string|null."
            ),
            "constraints": (
                "- Return ONLY valid JSON — no markdown fences, no commentary\n"
                "- Include both item_hash and code on every object\n"
                "- Enforce applicability: beverage fields null for food and vice versa\n"
                "- Do not change category, subcategory, title, or desc"
            ),
            "output_format": (
                '{\n'
                '  "items": [\n'
                "    {\n"
                '      "item_hash": "m:CODE",\n'
                '      "code": "CODE",\n'
                '      "item_type": "food|beverage",\n'
                '      "beverage_type": "alcoholic|non_alcoholic|null",\n'
                '      "is_vegetarian": "boolean|null",\n'
                '      "is_vegan": "boolean|null",\n'
                '      "is_localized": "boolean|null",\n'
                '      "localization_confidence": "0.0-1.0|null",\n'
                '      "localization_note": "string|null"\n'
                "    }\n"
                "  ]\n"
                "}"
            ),
            "example": _EXAMPLE_JSON,
        }
    )
    table = build_items_markdown_table(items)
    human_message = (
        f"Enrich these menu items for route {origin_iata}→{dest_iata}.\n"
        f"Localization target: {localization_target or 'none'}.\n\n"
        f"{table}"
    )
    return system_prompt, human_message


__all__ = [
    "MENU_ENRICHMENT_PROMPT_VERSION",
    "MENU_ENRICHMENT_VERSION",
    "build_items_markdown_table",
    "build_menu_enrichment_prompt",
]
