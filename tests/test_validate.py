"""Regression tests for empty-string coercion before Pydantic validation."""

from __future__ import annotations

from pathlib import Path

from pipeline.normalize import normalize_deterministic
from pipeline.parse_json import extract_aircraft_json
from pipeline.validate import sanitize_empty_values
from shared.schemas import AircraftConfiguration

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def test_sanitize_empty_values_coerces_top_level_string() -> None:
    assert sanitize_empty_values("") is None


def test_sanitize_empty_values_preserves_non_empty() -> None:
    assert sanitize_empty_values("2026-03-30") == "2026-03-30"
    assert sanitize_empty_values(0) == 0
    assert sanitize_empty_values(False) is False


def test_sanitize_empty_values_recurses_nested_structures() -> None:
    payload = {
        "last_updated": "",
        "cabins": {
            "economy": {"adjustable_headrest": "", "num_seats": 150},
        },
        "tags": ["", "active"],
    }
    result = sanitize_empty_values(payload)
    assert result == {
        "last_updated": None,
        "cabins": {
            "economy": {"adjustable_headrest": None, "num_seats": 150},
        },
        "tags": [None, "active"],
    }


def test_ai_321_empty_last_updated_validates() -> None:
    html = (DATA_DIR / "ai-321.html").read_text(encoding="utf-8")
    raw = extract_aircraft_json(html)
    assert raw is not None

    base = normalize_deterministic(raw, "ai", "Air India")
    aircraft = AircraftConfiguration.model_validate(base)

    assert aircraft.svg_id == "ai-321"
    assert aircraft.last_updated is None


def test_ai_319_2_empty_adjustable_headrest_validates() -> None:
    html = (DATA_DIR / "ai-319-2.html").read_text(encoding="utf-8")
    raw = extract_aircraft_json(html)
    assert raw is not None

    base = normalize_deterministic(raw, "ai", "Air India")
    aircraft = AircraftConfiguration.model_validate(base)

    assert aircraft.svg_id == "ai-319-2"
    assert aircraft.cabins["economy"].adjustable_headrest is None
