"""EPD-style prompt for AeroLOPA aircraft hardware normalization."""

from __future__ import annotations

import json
from typing import Any

from output import aircraft_hardware_features
from pipeline.prompts.base_prompt import generate_prompt
from pipeline.prompts.schema_format import build_output_format

_EXAMPLE_JSON = json.dumps(aircraft_hardware_features["ek-359g"], indent=2)
_DECK_EXAMPLE_JSON = json.dumps(aircraft_hardware_features["ek-388j-m"], indent=2)

_FIELD_DEFINITIONS = """### Aircraft-level fields
- svg_id: unique config id (e.g. ek-359g)
- airline_iata: 2-letter IATA code (EK, BA, AI)
- airline_name: full airline name
- iata_code: aircraft type code (359, 388, etc.)
- aircraft_type: full ICAO/manufacturer type string
- aircraft_type_displayed: marketing display name
- aircraft_code_displayed: short code shown in UI
- manufacturer: Airbus, Boeing, etc.
- haul_type: Long Haul, Short Haul, etc.
- lifecycle: active, retired, etc.
- is_dual_deck: boolean
- deck: "main" or "upper" for deck-specific pages (-m/-u suffix); null for single-deck
- parent_svg_id: base config id without deck suffix (e.g. ek-388j for ek-388j-m); null for single-deck
- deck_state: "complete" or "partial" when is_dual_deck is true; null otherwise
- fleet_count: integer count in fleet
- last_updated: ISO date YYYY-MM-DD
- configuration: seat-count shorthand — space-separated tokens of {count}{cabin_letter}. Letters: F=First, J=Business, W=Premium Economy, M=Economy. Example: "32J 21W 259M" means 32 business, 21 premium economy, 259 economy. Must align with seat_counts totals.
- description: free-text aircraft description
- total_seats: integer
- seat_counts: {first, business, premium_economy, economy, total} integers
- ife_provider / ife_system_name / ife_description: split IFE vendor vs product
- wifi_provider / wifi_system_name: split WiFi vendor vs product
- wifi: {technology, tier, rating, cost, fleet_pct} — object, NOT a list
- seat_rating_summary: {rated_seat_count, green_count, yellow_count, red_count}

### Deck-level fields (keys: main, upper)
- deck: "main" or "upper"
- svg_id: deck page id (e.g. ek-388j-m)
- seat_counts: deck-local counts only
- seat_rating_summary: ratings from that deck's seat map only
- cabins: cabin dict for cabins on this deck only

### Cabin-level fields (keys: first, business, premium_economy, economy)
- cabin_type: single letter (F, J, W, M)
- cabin_class: First, Business, Premium Economy, Economy
- num_seats: integer
- rows: source string (e.g. "01 to 08")
- row_start / row_end: integers parsed from rows
- layout: seat abreast pattern — hyphen-separated digits per row (e.g. "1-2-1", "2-3-2", "3-3-3"). Derive from source layout field or seat_description ("arranged 1-2-1")
- seat_manufacturer: maker only (Safran, Recaro, Collins)
- pitch_inch / width_inch: numbers in inches
- recline_inch / recline_deg: number OR null (degrees if value contains °)
- has_flat_bed: boolean
- bed_flat_length_inch: number or null
- screen_size_inch: number parsed from screen description
- screen_description: original screen text
- ife_provider / ife_system_name / ife: cabin IFE fields
- wifi_provider / wifi_system_name / wifi_description: cabin WiFi fields
- power_v: integer volts or null if not equipped
- power_description: original power text
- usb_a_availability / usb_a_count / usb_c_availability / usb_c_count: split USB types
- usb_description: original USB text
- bluetooth_connectivity / wireless_charging / privacy_doors / personal_gasper_vent: Yes/No strings
- adjustable_headrest / adjustable_armrests: boolean
- adjustable_headrest_description / adjustable_armrests_description: text
- direct_aisle_access_pct: integer 0-100
- seat_description: free-text seat details"""

_SEARCH_PATTERNS = """- Row ranges: "01 to 08", "14-16" → row_start=1, row_end=8
- Measurements: '23" 4K UHD' → screen_size_inch=23; "44 inch" → pitch_inch=44
- USB: "USB-A (10W) and two USB-C (60W)" → usb_a_availability=true, usb_a_count=1, usb_c_availability=true, usb_c_count=2
- IFE/WiFi: "Thales Avant" → provider=Thales, system_name=Avant
- WiFi vendors: Viasat, Inmarsat, Panasonic, Gogo, Intelsat, Starlink
- Flat bed: recline_deg=180 or "flat bed" in description → has_flat_bed=true
- Power: "110V universal AC" → power_v=110; blank/Not equipped → power_v=null
- wifi array in source: take first element as wifi object
- Aircraft configuration string at top level or in description (e.g. "32J 21W 259M")
- Cabin layout in layout key or embedded in seat_description ("arranged 3-3-3")"""

_CONSTRAINTS = """- Return ONLY valid JSON — no markdown fences, no commentary
- Use correct JSON types: numbers as numbers, booleans as booleans, null for missing
- Do NOT wrap wifi in a list; use a single object
- Cabin keys must be lowercase snake_case: first, business, premium_economy, economy
- Include ALL fields where source data exists; do not omit populated fields
- Do not invent data; use null for genuinely missing values
- Preserve original description strings alongside parsed numeric fields
- If USB count is unstated but type is present, infer count=1
- last_updated must be YYYY-MM-DD (strip time component if present)
- Ensure that the output structure is exactly as specified in the output_format section
- configuration and each cabin layout are required when source data exists; do not omit or paraphrase
- configuration must use standard cabin letters (F/J/W/M), not full words
- layout must use hyphen-separated digits only (e.g. 3-3-3, not 3x3x3)
- For deck pages (-m/-u), seat_counts, configuration, rows, and cabins must reflect that deck only — do not merge cross-deck data
- Populate decks.{deck}.cabins with deck-local cabins; mirror the same cabins in the top-level cabins dict"""


def build_aircraft_hardware_prompt(
    raw: dict[str, Any],
    airline_slug: str,
) -> tuple[str, str]:
    """Return (system_prompt, human_message) for LLM normalization."""
    sections = {
        "role": (
            "You are an expert aviation data extraction assistant. "
            "Convert raw AeroLOPA aircraft configuration JSON into a normalized "
            "hardware-features schema used for airline fleet benchmarking."
        ),
        "context": (
            "Input is cleaned AeroLOPA JSON extracted from HTML seat-map pages. "
            "Per-seat maps, image URLs, and asset metadata have been removed. "
            "Fields use inconsistent naming, mixed units, and nested structures. "
            "Your output feeds a Postgres database and comparison UI."
        ),
        "instructions": (
            "1. Read the cleaned raw JSON below.\n"
            "2. Map every available field to the target schema.\n"
            "3. Parse measurements, row ranges, USB splits, and IFE/WiFi provider splits.\n"
            "4. Normalize cabin keys to first/business/premium_economy/economy.\n"
            "5. Extract configuration (e.g. 32J 21W 259M) and each cabin layout (e.g. 1-2-1) exactly as specified.\n"
            "6. Verify configuration matches seat_counts and cabin layouts match source data.\n"
            "7. Validate extracted data against the output_format schema before outputting.\n"
            "8. Return only the normalized JSON object — no markdown fences or commentary."
        ),
        "field_definitions": _FIELD_DEFINITIONS,
        "search_patterns": _SEARCH_PATTERNS,
        "constraints": _CONSTRAINTS,
        "output_format": build_output_format(),
        "example": (
            f"Reference output for ek-359g (single-deck Emirates A350-900):\n```json\n{_EXAMPLE_JSON}\n```\n\n"
            f"Reference output for ek-388j-m (dual-deck A380 main deck):\n```json\n{_DECK_EXAMPLE_JSON}\n```"
        ),
    }

    system_prompt = generate_prompt(sections)
    human_message = (
        f"Airline slug: {airline_slug}\n\n"
        "<aerolopa_raw_json>\n"
        f"{json.dumps(raw, indent=2)}\n"
        "</aerolopa_raw_json>"
    )
    return system_prompt, human_message
