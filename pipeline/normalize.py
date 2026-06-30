"""Normalize raw AeroLOPA JSON into AircraftConfiguration schema."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from pipeline.clean import clean_raw_for_llm
from pipeline.deck import deck_from_svg_id, is_deck_page, parent_svg_id_from_svg_id
from pipeline.prompts.aircraft_hardware_prompt import build_aircraft_hardware_prompt
from pipeline.validate import sanitize_empty_values, tolerant_validate_aircraft
from shared.schemas import AircraftConfiguration

logger = logging.getLogger(__name__)

IFE_VENDORS = ("Thales", "Panasonic", "Safran", "Collins", "Gogo", "Intelsat")
WIFI_VENDORS = ("Viasat", "Inmarsat", "Panasonic", "Gogo", "Intelsat", "Starlink")


@dataclass
class NormalizeResult:
    aircraft: AircraftConfiguration
    source: str  # "llm" or "deterministic"
    llm_parsed: dict[str, Any] | None = None
    dropped_fields: list[str] | None = None
    cleaned_raw: dict[str, Any] | None = None


def _parse_rows(rows: str | None) -> tuple[int | None, int | None]:
    if not rows:
        return None, None
    match = re.search(r"(\d+)\s*(?:to|-)\s*(\d+)", rows, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def _parse_inches(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"([\d.]+)", str(value))
    return float(match.group(1)) if match else None


def _parse_voltage(value: Any) -> int | None:
    if value is None or str(value).strip() in ("", "Not equipped"):
        return None
    match = re.search(r"(\d+)", str(value))
    return int(match.group(1)) if match else None


def _parse_recline(value: Any) -> tuple[float | None, float | None]:
    if value is None:
        return None, None
    text = str(value)
    if "°" in text or "deg" in text.lower():
        deg = _parse_inches(text)
        return None, deg
    return _parse_inches(text), None


def _parse_screen_size(screen_info: str | None) -> float | None:
    if not screen_info:
        return None
    match = re.search(r'([\d.]+)\s*"', screen_info)
    return float(match.group(1)) if match else _parse_inches(screen_info)


def _parse_usb(usb: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "usb_description": usb,
        "usb_a_availability": False,
        "usb_a_count": None,
        "usb_c_availability": False,
        "usb_c_count": None,
    }
    if not usb:
        return result
    lower = usb.lower()
    if "usb-a" in lower or "usb a" in lower:
        result["usb_a_availability"] = True
        count_match = re.search(r"(\d+)\s*usb-a", lower)
        if count_match:
            result["usb_a_count"] = int(count_match.group(1))
        elif re.search(r"two usb-a|2 usb-a", lower):
            result["usb_a_count"] = 2
        elif "one usb-a" in lower or "a usb-a" in lower:
            result["usb_a_count"] = 1
        else:
            result["usb_a_count"] = 1
    if "usb-c" in lower or "usb c" in lower:
        result["usb_c_availability"] = True
        count_match = re.search(r"(\d+)\s*usb-c", lower)
        if count_match:
            result["usb_c_count"] = int(count_match.group(1))
        elif re.search(r"two usb-c|2 usb-c", lower):
            result["usb_c_count"] = 2
        else:
            result["usb_c_count"] = 1
    return result


def _split_provider_system(text: str | None, vendors: tuple[str, ...]) -> tuple[str | None, str | None]:
    if not text:
        return None, None
    for vendor in vendors:
        if vendor.lower() in text.lower():
            remainder = re.sub(re.escape(vendor), "", text, count=1, flags=re.IGNORECASE).strip()
            system = remainder.split()[0] if remainder else None
            return vendor, system or None
    return None, None


def _parse_wifi_fields(wifi_raw: Any) -> tuple[dict[str, Any] | None, str | None, str | None]:
    wifi_obj = None
    if isinstance(wifi_raw, list) and wifi_raw:
        wifi_obj = wifi_raw[0] if isinstance(wifi_raw[0], dict) else None
    elif isinstance(wifi_raw, dict):
        wifi_obj = wifi_raw

    if not wifi_obj:
        return None, None, None

    tech = wifi_obj.get("technology") or ""
    provider, system = _split_provider_system(tech, WIFI_VENDORS)
    if not provider and tech:
        if "global xpress" in tech.lower() or "gx" in tech.lower():
            provider, system = "Viasat", "Global Xpress"
    return wifi_obj, provider, system


def _aggregate_seat_ratings(seats: Any) -> dict[str, int] | None:
    if not isinstance(seats, dict):
        return None
    green = yellow = red = 0
    for seat in seats.values():
        if not isinstance(seat, dict):
            continue
        rating = (seat.get("rating") or "").lower()
        if rating == "green":
            green += 1
        elif rating == "yellow":
            yellow += 1
        elif rating == "red":
            red += 1
    total = green + yellow + red
    if total == 0:
        return None
    return {
        "rated_seat_count": total,
        "green_count": green,
        "yellow_count": yellow,
        "red_count": red,
    }


def _cabin_key(cabin_class: str) -> str:
    mapping = {
        "first": "first",
        "business": "business",
        "premium economy": "premium_economy",
        "economy": "economy",
    }
    return mapping.get(cabin_class.lower().replace(" seats", "").strip(), cabin_class.lower())


def _normalize_cabin(cabin: dict[str, Any], cabin_class: str, key: str) -> dict[str, Any]:
    row_start, row_end = _parse_rows(cabin.get("rows"))
    recline_inch, recline_deg = _parse_recline(cabin.get("recline"))
    screen_desc = cabin.get("screen_info") or cabin.get("screen_description")
    usb_fields = _parse_usb(cabin.get("usb"))

    ife_text = cabin.get("ife") or cabin.get("ife_description")
    ife_provider, ife_system = _split_provider_system(ife_text, IFE_VENDORS)
    wifi_text = cabin.get("wifi") or cabin.get("wifi_description")
    wifi_provider, wifi_system = _split_provider_system(wifi_text, WIFI_VENDORS)

    has_flat_bed = cabin.get("has_flat_bed", False)
    if not has_flat_bed and (recline_deg == 180 or "flat bed" in str(cabin.get("seat_description", "")).lower()):
        has_flat_bed = True

    return {
        "cabin_type": cabin.get("cabin_type", ""),
        "cabin_class": cabin_class or key.replace("_", " ").title(),
        "num_seats": cabin.get("num_seats", 0),
        "rows": cabin.get("rows"),
        "row_start": row_start,
        "row_end": row_end,
        "layout": cabin.get("layout"),
        "seat_manufacturer": cabin.get("seat_manufacturer"),
        "pitch_inch": _parse_inches(cabin.get("pitch")),
        "width_inch": _parse_inches(cabin.get("width")),
        "recline_inch": recline_inch,
        "recline_deg": recline_deg,
        "has_flat_bed": has_flat_bed,
        "bed_flat_length_inch": _parse_inches(cabin.get("bed_flat_length_inch") or cabin.get("bed_length")),
        "screen_size_inch": _parse_screen_size(screen_desc),
        "screen_description": screen_desc,
        "ife_provider": cabin.get("ife_provider") or ife_provider,
        "ife_system_name": cabin.get("ife_system_name") or ife_system,
        "ife": ife_text,
        "wifi_provider": cabin.get("wifi_provider") or wifi_provider,
        "wifi_system_name": cabin.get("wifi_system_name") or wifi_system,
        "wifi_description": wifi_text if isinstance(wifi_text, str) else None,
        "power_v": _parse_voltage(cabin.get("power")),
        "power_description": cabin.get("power") if isinstance(cabin.get("power"), str) else cabin.get("power_description"),
        "bluetooth_connectivity": cabin.get("bluetooth_connectivity") or cabin.get("bluetooth"),
        "wireless_charging": cabin.get("wireless_charging"),
        "privacy_doors": cabin.get("privacy_doors"),
        "personal_gasper_vent": cabin.get("personal_gasper_vent") or cabin.get("gasper"),
        "adjustable_headrest": cabin.get("adjustable_headrest"),
        "adjustable_headrest_description": cabin.get("adjustable_headrest_description"),
        "adjustable_armrests": cabin.get("adjustable_armrests"),
        "adjustable_armrests_description": cabin.get("adjustable_armrests_description"),
        "direct_aisle_access_pct": cabin.get("direct_aisle_access_pct"),
        "seat_description": cabin.get("seat_description"),
        **usb_fields,
    }


def _normalize_seat_counts(seat_counts_raw: Any) -> dict[str, int]:
    if isinstance(seat_counts_raw, dict):
        return {
            "first": seat_counts_raw.get("first", 0),
            "business": seat_counts_raw.get("business", 0),
            "premium_economy": seat_counts_raw.get("premium_economy", 0),
            "economy": seat_counts_raw.get("economy", 0),
            "total": seat_counts_raw.get("total", 0),
        }
    return {"first": 0, "business": 0, "premium_economy": 0, "economy": 0, "total": 0}


def _normalize_cabins_from_raw(cabins_raw: Any) -> dict[str, Any]:
    cabins_out: dict[str, Any] = {}
    if isinstance(cabins_raw, list):
        for cabin in cabins_raw:
            if not isinstance(cabin, dict):
                continue
            cabin_class = (cabin.get("cabin_class") or "").replace(" seats", "").strip()
            key = _cabin_key(cabin_class)
            cabins_out[key] = _normalize_cabin(cabin, cabin_class, key)
    elif isinstance(cabins_raw, dict):
        for key, cabin in cabins_raw.items():
            if isinstance(cabin, dict):
                cabin_class = (cabin.get("cabin_class") or key.replace("_", " ")).replace(" seats", "").strip()
                cabins_out[key] = _normalize_cabin(cabin, cabin_class, key)
    return cabins_out


def _scope_raw_to_deck(raw: dict[str, Any], svg_id: str) -> dict[str, Any]:
    """Prefer per-deck fields from decks[] when parent payload is merged."""
    if not is_deck_page(svg_id):
        return raw

    decks = raw.get("decks")
    if not isinstance(decks, list):
        return raw

    for entry in decks:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("svg_id") or entry.get("aircraft_code")
        if entry_id != svg_id:
            continue
        scoped = dict(raw)
        for key in ("seat_counts", "total_seats", "configuration", "seats", "cabins"):
            if entry.get(key) is not None:
                scoped[key] = entry[key]
        return scoped
    return raw


def _parse_deck_state(raw: dict[str, Any]) -> str | None:
    state = raw.get("deck_state")
    if state == "complete":
        return "complete"
    if state:
        return "partial"
    return None


def normalize_deterministic(raw: dict[str, Any], airline_slug: str, airline_name: str) -> dict[str, Any]:
    """Best-effort deterministic normalization without LLM."""
    svg_id = raw.get("svg_id") or raw.get("aircraft_code") or ""
    scoped = _scope_raw_to_deck(raw, svg_id)
    airline_iata = scoped.get("airline_iata") or airline_slug.upper()

    seat_counts = _normalize_seat_counts(scoped.get("seat_counts"))

    wifi, wifi_provider, wifi_system = _parse_wifi_fields(scoped.get("wifi"))
    ife_provider, ife_system = _split_provider_system(scoped.get("ife_description"), IFE_VENDORS)
    seat_rating = _aggregate_seat_ratings(scoped.get("seats"))

    cabins_out = _normalize_cabins_from_raw(scoped.get("cabins") or [])

    last_updated = scoped.get("last_updated")
    if last_updated and isinstance(last_updated, str) and "T" in last_updated:
        last_updated = last_updated.split("T")[0]

    deck = deck_from_svg_id(svg_id)
    parent_id = parent_svg_id_from_svg_id(svg_id)
    is_dual_deck = scoped.get("is_dual_deck", False)
    deck_state = _parse_deck_state(scoped) if is_dual_deck else None

    decks_out: dict[str, Any] = {}
    if deck:
        decks_out[deck] = {
            "deck": deck,
            "svg_id": svg_id,
            "seat_counts": seat_counts,
            "seat_rating_summary": seat_rating,
            "cabins": cabins_out,
        }

    return sanitize_empty_values(
        {
            "svg_id": svg_id,
            "airline_iata": airline_iata,
            "airline_name": scoped.get("airline_name") or airline_name,
            "iata_code": scoped.get("iata_code"),
            "aircraft_type": scoped.get("aircraft_type"),
            "aircraft_type_displayed": scoped.get("aircraft_type_displayed"),
            "aircraft_code_displayed": scoped.get("aircraft_code_displayed"),
            "manufacturer": scoped.get("manufacturer") or scoped.get("aircraft_manufacturer"),
            "haul_type": scoped.get("haul_type"),
            "lifecycle": scoped.get("lifecycle", "active"),
            "is_dual_deck": is_dual_deck,
            "deck": deck,
            "parent_svg_id": parent_id,
            "deck_state": deck_state,
            "fleet_count": scoped.get("fleet_count"),
            "last_updated": last_updated,
            "configuration": scoped.get("configuration"),
            "description": scoped.get("description"),
            "total_seats": scoped.get("total_seats") or seat_counts.get("total"),
            "seat_counts": seat_counts,
            "ife_provider": scoped.get("ife_provider") or ife_provider,
            "ife_system_name": scoped.get("ife_system_name") or ife_system,
            "ife_description": scoped.get("ife_description"),
            "wifi_provider": scoped.get("wifi_provider") or wifi_provider,
            "wifi_system_name": scoped.get("wifi_system_name") or wifi_system,
            "wifi": wifi,
            "seat_rating_summary": seat_rating,
            "decks": decks_out,
            "cabins": cabins_out,
        }
    )


def _coerce_wifi_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, list) and value:
        value = value[0]
    if isinstance(value, dict):
        return value
    return None


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == {} or value == []


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Merge overlay onto base; overlay non-empty values win, recurse into cabins/decks."""
    merged = dict(base)
    for key, value in overlay.items():
        if key == "cabins" and isinstance(value, dict):
            base_cabins = merged.get("cabins") or {}
            merged_cabins = dict(base_cabins)
            for cabin_key, cabin_overlay in value.items():
                if not isinstance(cabin_overlay, dict):
                    continue
                base_cabin = merged_cabins.get(cabin_key) or {}
                merged_cabins[cabin_key] = _deep_merge(base_cabin, cabin_overlay)
            merged["cabins"] = merged_cabins
        elif key == "decks" and isinstance(value, dict):
            base_decks = merged.get("decks") or {}
            merged_decks = dict(base_decks)
            for deck_key, deck_overlay in value.items():
                if not isinstance(deck_overlay, dict):
                    continue
                base_deck = merged_decks.get(deck_key) or {}
                merged_decks[deck_key] = _deep_merge(base_deck, deck_overlay)
            merged["decks"] = merged_decks
        elif key == "seat_counts" and isinstance(value, dict):
            base_counts = merged.get("seat_counts") or {}
            merged["seat_counts"] = {**base_counts, **{k: v for k, v in value.items() if not _is_empty(v)}}
        elif key == "wifi":
            coerced = _coerce_wifi_dict(value)
            if coerced is not None:
                base_wifi = merged.get("wifi") or {}
                if isinstance(base_wifi, dict):
                    merged["wifi"] = {**base_wifi, **{k: v for k, v in coerced.items() if not _is_empty(v)}}
                else:
                    merged["wifi"] = coerced
        elif not _is_empty(value):
            merged[key] = value
    return merged


def normalize_with_llm(
    raw: dict[str, Any],
    airline_slug: str,
    airline_name: str,
    model: str | None = None,
) -> NormalizeResult:
    """Normalize raw JSON; LLM output is deep-merged over deterministic base."""
    model_name = model or os.getenv("LLM_MODEL", "gemini-2.5-pro")
    api_key = os.getenv("GOOGLE_API_KEY")

    base = normalize_deterministic(raw, airline_slug, airline_name)
    cleaned = clean_raw_for_llm(raw)

    if not api_key:
        logger.info("GOOGLE_API_KEY not set; using deterministic normalization only")
        return NormalizeResult(
            aircraft=AircraftConfiguration.model_validate(base),
            source="deterministic",
            cleaned_raw=cleaned,
        )

    try:
        system_prompt, human_message = build_aircraft_hardware_prompt(cleaned, airline_slug)
        llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_message),
        ]
        response = llm.invoke(messages)
        content = response.content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
        parsed = json.loads(content, strict=False)
        merged = _deep_merge(base, parsed)
        aircraft, dropped_fields = tolerant_validate_aircraft(merged, base)
        if dropped_fields:
            logger.info("Tolerant validation dropped %d field(s): %s", len(dropped_fields), dropped_fields)
        return NormalizeResult(
            aircraft=aircraft,
            source="llm",
            llm_parsed=parsed,
            dropped_fields=dropped_fields or None,
            cleaned_raw=cleaned,
        )
    except Exception as exc:
        logger.warning("LLM normalization failed (%s); using deterministic fallback", exc)
        return NormalizeResult(
            aircraft=AircraftConfiguration.model_validate(base),
            source="deterministic",
            cleaned_raw=cleaned,
        )
