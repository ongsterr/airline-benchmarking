"""Strip noise from parsed AeroLOPA JSON before LLM normalization."""

from __future__ import annotations

from typing import Any

_AIRCRAFT_KEYS = frozenset(
    {
        "svg_id",
        "aircraft_code",
        "airline_iata",
        "iata_code",
        "aircraft_type",
        "aircraft_type_displayed",
        "aircraft_code_displayed",
        "aircraft_manufacturer",
        "manufacturer",
        "haul_type",
        "lifecycle",
        "is_dual_deck",
        "deck_state",
        "missing_deck",
        "decks",
        "fleet_count",
        "last_updated",
        "configuration",
        "description",
        "total_seats",
        "seat_counts",
        "wifi",
        "ife_description",
        "cabins",
    }
)

_CABIN_DROP_SUFFIXES = ("_info",)


def _clean_cabin(cabin: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in cabin.items():
        if value is None:
            continue
        if key.endswith(_CABIN_DROP_SUFFIXES) and value == "":
            continue
        cleaned[key] = value
    return cleaned


def _clean_cabins(cabins: Any) -> list[dict[str, Any]] | dict[str, Any] | None:
    if isinstance(cabins, list):
        return [_clean_cabin(c) for c in cabins if isinstance(c, dict)]
    if isinstance(cabins, dict):
        return {key: _clean_cabin(c) for key, c in cabins.items() if isinstance(c, dict)}
    return None


def _clean_decks(decks: Any) -> list[dict[str, Any]] | None:
    if not isinstance(decks, list):
        return None
    cleaned_decks: list[dict[str, Any]] = []
    for deck in decks:
        if not isinstance(deck, dict):
            continue
        cleaned_deck: dict[str, Any] = {}
        for key, value in deck.items():
            if key in ("seats", "image_url", "image_url_cdn", "image_url_neutral_cdn", "svg_url", "seat_rects_url"):
                continue
            if key == "cabins":
                cabins = _clean_cabins(value)
                if cabins:
                    cleaned_deck[key] = cabins
                continue
            if value is None:
                continue
            cleaned_deck[key] = value
        if cleaned_deck:
            cleaned_decks.append(cleaned_deck)
    return cleaned_decks or None


def clean_raw_for_llm(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a compact payload for the LLM — no seats map, URLs, or asset noise."""
    cleaned: dict[str, Any] = {}
    for key in _AIRCRAFT_KEYS:
        if key not in raw:
            continue
        value = raw[key]
        if key == "cabins":
            cabins = _clean_cabins(value)
            if cabins:
                cleaned[key] = cabins
            continue
        if key == "decks":
            decks = _clean_decks(value)
            if decks:
                cleaned[key] = decks
            continue
        if value is None:
            continue
        cleaned[key] = value

    if "manufacturer" not in cleaned and raw.get("aircraft_manufacturer"):
        cleaned["manufacturer"] = raw["aircraft_manufacturer"]

    return cleaned
