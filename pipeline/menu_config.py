"""Configuration for Emirates F&B menu extraction pipeline."""

from __future__ import annotations

from datetime import date

from pipeline.config import PROJECT_ROOT

MENU_AIRLINE_SLUG = "ek"
MENU_AIRLINE_IATA = "EK"
MENU_AIRLINE_NAME = "Emirates"
MENU_SOURCE_ID = "emirates_dining_onboard"

MENU_BASE_URL = "https://www.emirates.com/ae/english/experience/dining/onboard-menu/"
MENU_URL_TEMPLATE = (
    "{base}?date={date}&flight={flight}&origin={origin}"
    "&destination={destination}&cabinclass={cabin_code}&view=1"
)

# Digital menu JSON API (public POST; page HTML is JS-rendered shell only)
MENU_API_URL = "https://www.emirates.com/service/exp/digital-menu"
MENU_API_LANG = "en"

# Emirates cabinclass query / API cabinClass values
MENU_CABIN_CODES: dict[str, str] = {
    "first": "f",
    "business": "j",
    "premium_economy": "w",
    "economy": "y",
}

MENU_CABIN_MARKETING: dict[str, str] = {
    "first": "First Class",
    "business": "Business Class",
    "premium_economy": "Premium Economy",
    "economy": "Economy Class",
}

STANDARD_MENU_CABINS = tuple(MENU_CABIN_CODES.keys())

MENU_HUB_IATA = "DXB"

# Gemini model for blank-title description expansion only (not hardware/flight)
DEFAULT_MENU_LLM_MODEL = "gemini-3.5-flash"

MENU_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "menu"
MENU_PARSED_DIR = PROJECT_ROOT / "data" / "parsed" / "menu"
MENU_EVIDENCE_DIR = PROJECT_ROOT / "evidence" / "emirates"

_MONTH_ABBR = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def format_api_scheduled_date(service_date: date) -> str:
    """Emirates digital-menu API expects YYYY-MMM-DD (e.g. 2026-Aug-01)."""
    return f"{service_date.year}-{_MONTH_ABBR[service_date.month - 1]}-{service_date.day:02d}"


__all__ = [
    "MENU_AIRLINE_IATA",
    "MENU_AIRLINE_NAME",
    "MENU_AIRLINE_SLUG",
    "MENU_API_LANG",
    "MENU_API_URL",
    "MENU_BASE_URL",
    "MENU_CABIN_CODES",
    "MENU_CABIN_MARKETING",
    "MENU_EVIDENCE_DIR",
    "MENU_HUB_IATA",
    "DEFAULT_MENU_LLM_MODEL",
    "MENU_PARSED_DIR",
    "MENU_RAW_DIR",
    "MENU_SOURCE_ID",
    "MENU_URL_TEMPLATE",
    "STANDARD_MENU_CABINS",
    "format_api_scheduled_date",
]
