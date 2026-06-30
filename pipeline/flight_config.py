"""Configuration for cabin flight features pipeline."""

from pathlib import Path

from pipeline.config import AIRLINE_NAMES, DEFAULT_AIRLINES, PROJECT_ROOT

FLIGHT_PARSED_DIR = PROJECT_ROOT / "data" / "parsed" / "flight"

STANDARD_CABIN_KEYS = ("first", "business", "premium_economy", "economy")

__all__ = [
    "AIRLINE_NAMES",
    "DEFAULT_AIRLINES",
    "FLIGHT_PARSED_DIR",
    "STANDARD_CABIN_KEYS",
]
