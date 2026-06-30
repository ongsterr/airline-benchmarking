"""EPD-style prompt for airline cabin flight feature web research."""

from __future__ import annotations

import json

from output import aircraft_flight_features
from pipeline.prompts.base_prompt import generate_prompt
from pipeline.prompts.flight_schema_format import build_flight_research_output_format

_SAMPLE_SOURCES = [
    {
        "url": "https://www.emirates.com/uk/english/before-you-fly/baggage/",
        "title": "Baggage allowance",
        "publisher": "emirates.com",
    },
    {
        "url": "https://www.emirates.com/uk/english/experience/cabin-features/first-class/",
        "title": "First Class cabin features",
        "publisher": "emirates.com",
    },
]

_EXAMPLE_PAYLOAD: dict = {}
for cabin_key, cabin_data in aircraft_flight_features.items():
    _EXAMPLE_PAYLOAD[cabin_key] = {
        "cabin_class": cabin_data["cabin_class"],
        "sources": _SAMPLE_SOURCES,
        "features": cabin_data["features"],
    }
_EXAMPLE_JSON = json.dumps(_EXAMPLE_PAYLOAD, indent=2)

_FIELD_DEFINITIONS = """### Per-cabin structure (keys: first, business, premium_economy, economy)
Each cabin entry contains:
- cabin_class: First, Business, Premium Economy, Economy
- sources: array of at least 5 credible source objects (url, title, publisher)
- features: nested object with flight benefit fields below

### Feature fields (inside features)
- check-in_priority: Yes/No — priority check-in desk access
- cabin_bag_pieces: integer count of carry-on bags allowed
- cabin_bag_kg_per_piece: kg weight limit per carry-on piece
- cabin_bag_kg_total: total carry-on weight if stated separately
- checked_bag_pieces: integer count of checked bags included
- checked_bag_kg_per_piece: kg per checked bag
- checked_bag_kg_total: total checked baggage allowance if stated
- boarding_priority: Yes/No — priority boarding
- lounge_access: Yes/No — airport lounge access included
- amenity_kit: array of amenity items (toothbrush, eyemask, etc.) or null
- amenity_kit_brand: brand name (e.g. Bulgari) or null"""

_SEARCH_PATTERNS = """### Credible source types (prioritize in this order)
1. Official airline website — baggage, cabin product, lounge, check-in pages
2. Airline help centre / travel-info subdomains on the same domain
3. Airline press releases or media pages for amenity kit / product launches
4. Reputable aviation or travel publications (e.g. airline-specific product reviews from established outlets)
5. IATA or government transport authority pages only when airline site is silent

### Search query patterns (run per cabin class)
- "{airline_name} first class baggage allowance"
- "{airline_name} business class lounge access"
- "{airline_name} premium economy carry-on weight"
- "{airline_name} economy checked baggage pieces"
- "{airline_name} amenity kit brand business class"

### Field extraction patterns
- "2 x 23kg" → checked_bag_pieces=2, checked_bag_kg_per_piece=23
- "50kg total" without per-piece → checked_bag_kg_total=50
- "7kg carry-on" → cabin_bag_kg_per_piece=7
- Priority / Fast Track / dedicated check-in → check_in_priority=Yes
- Lounge / Skywards lounge / Club lounge → lounge_access=Yes
- Priority boarding / Group 1 → boarding_priority=Yes
- Amenity kit contents as bullet list → amenity_kit array; brand name → amenity_kit_brand

### Conflict resolution
- Prefer official airline pages over third-party sources
- When sources disagree, use the most recent official airline policy
- Prioritize the most up-to-date data: prefer pages with recent publish/update dates, current policy years, or "effective from" dates over outdated or undated content
- Deprioritize archived pages, old press releases, and third-party articles that may reflect superseded policies
- Do not average or blend conflicting numbers"""

_CONSTRAINTS = """- Return ONLY valid JSON — no markdown fences, no commentary
- Top-level keys must be cabin slugs: first, business, premium_economy, economy
- Include at least 5 credible sources per cabin in the sources array
- Each source must have url, title, and publisher
- Extract the most up-to-date values available; do not use outdated baggage, lounge, or amenity policies when newer official sources exist
- Nest all benefit fields inside features (not at cabin top level)
- Use Yes/No strings for priority and access fields
- Use null for genuinely missing values; do not invent data
- Numbers must be JSON numbers, not strings
- amenity_kit must be a JSON array of strings or null
- Include all cabin classes the airline operates; omit cabins the airline does not offer
- Use check-in_priority (hyphen) inside features to match the output schema"""


def build_flight_features_research_prompt(
    airline_slug: str,
    airline_name: str,
) -> tuple[str, str]:
    sections = {
        "role": (
            "You are an expert aviation product analyst. Research airline cabin-class "
            "flight benefits (baggage, check-in, boarding, lounge, amenity kits) using "
            "web search and return structured JSON for airline fleet benchmarking."
        ),
        "context": (
            f"Target airline: {airline_name} (slug: {airline_slug}). "
            "Flight features are airline-wide policy per cabin class, not aircraft-specific. "
            "Your output feeds a Postgres database and airline comparison UI."
        ),
        "instructions": (
            "1. Use web search to find credible sources for each cabin class this airline operates.\n"
            "2. Collect at least 5 credible sources per cabin class.\n"
            "3. Prioritize the most up-to-date sources and policy data — current airline website pages "
            "and recently updated help/travel-info over older or undated third-party content.\n"
            "4. Extract all feature fields from those sources into the features object per cabin.\n"
            "5. Prefer official airline website pages; resolve conflicts in favor of the airline's own site.\n"
            "6. Validate the JSON against the output_format schema before responding.\n"
            "7. Return only the JSON object — no markdown fences or commentary."
        ),
        "field_definitions": _FIELD_DEFINITIONS,
        "search_patterns": _SEARCH_PATTERNS,
        "constraints": _CONSTRAINTS,
        "output_format": build_flight_research_output_format(),
        "example": f"Reference output (Emirates example with sample sources):\n```json\n{_EXAMPLE_JSON}\n```",
    }
    system_prompt = generate_prompt(sections)
    human_message = (
        f"Airline: {airline_name} (slug: {airline_slug})\n\n"
        "Research cabin-class flight benefits for this airline using web search."
    )
    return system_prompt, human_message
