"""Prompt for expanding blank-title Emirates menu items from descriptions."""

from __future__ import annotations

import json
from typing import Any

from pipeline.prompts.base_prompt import generate_prompt

MENU_BLANK_TITLE_PROMPT_VERSION = "menu_blank_title_prompt_v1"

_EXAMPLE_JSON = """{
  "expansions": {
    "BV000112": [
      {"title": "Orange juice", "desc": null},
      {"title": "Pineapple juice", "desc": null},
      {"title": "Apple juice", "desc": null},
      {"title": "Mango juice", "desc": null},
      {"title": "Tomato juice", "desc": null},
      {"title": "Cola", "desc": null},
      {"title": "Diet cola", "desc": null},
      {"title": "Lemonade", "desc": null},
      {"title": "Ginger ale", "desc": null},
      {"title": "Soda water", "desc": null},
      {"title": "Tonic water", "desc": null},
      {"title": "Still water", "desc": null},
      {"title": "Sparkling water", "desc": null}
    ]
  }
}"""


def build_menu_blank_title_expansion_prompt(
    candidates: list[dict[str, Any]],
    *,
    cabin_norm: str,
    cabin_marketing: str | None = None,
) -> tuple[str, str]:
    """Build system + human messages for blank-title expansion.

    Each candidate must include: base_code, category, subcategory, desc.
    """
    system_prompt = generate_prompt(
        {
            "role": (
                "You expand Emirates digital-menu items that have an empty title "
                "but a filled description into one or more concrete menu items."
            ),
            "context": (
                f"Cabin: {cabin_norm}"
                + (f" ({cabin_marketing})" if cabin_marketing else "")
                + ". Candidates already have cleaned text. Category and subcategory "
                "are fixed and must not change."
            ),
            "instructions": (
                "For each candidate, split the description into the individual "
                "products or dishes it lists.\n"
                "- Prefer one row per distinct drink or dish name.\n"
                "- Use 'or' / commas / line breaks as split cues when they list alternatives.\n"
                "- Put serving notes into desc when useful; otherwise set desc to null.\n"
                "- Do NOT invent products that are not supported by the description.\n"
                "- Do NOT return category, subcategory, or codes — only title and desc "
                "under each base_code key.\n"
                "- Return every candidate base_code exactly once as a key under expansions."
            ),
            "field_definitions": (
                "expansions: object keyed by base_code (string).\n"
                "expansions[base_code]: array of {title: string, desc: string|null}.\n"
                "title: required non-empty cleaned item name (no HTML).\n"
                "desc: optional cleaned serving detail, or null."
            ),
            "search_patterns": (
                "Example: 'Orange, pineapple, apple, mango or tomato Cola and diet cola, "
                "lemonade...' → separate juice and soft-drink titles."
            ),
            "constraints": (
                "- Return ONLY valid JSON — no markdown fences, no commentary\n"
                "- Keys under expansions MUST be the provided base_code values only\n"
                "- Each title must be non-empty after cleaning\n"
                "- Do not invent free-form codes or change category/subcategory\n"
                "- Do not drop a candidate key; if unsure, emit one best-effort title "
                "derived from the description"
            ),
            "output_format": (
                '{\n'
                '  "expansions": {\n'
                '    "<base_code>": [\n'
                '      {"title": "<string>", "desc": "<string>|null"}\n'
                "    ]\n"
                "  }\n"
                "}"
            ),
            "example": _EXAMPLE_JSON,
        }
    )
    human_message = (
        "Expand these blank-title menu candidates into discrete items:\n\n"
        f"{json.dumps(candidates, indent=2, ensure_ascii=False)}"
    )
    return system_prompt, human_message


__all__ = [
    "MENU_BLANK_TITLE_PROMPT_VERSION",
    "build_menu_blank_title_expansion_prompt",
]
