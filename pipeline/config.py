"""Pipeline configuration."""

from pathlib import Path

BASE_URL = "https://www.aerolopa.com"
DEFAULT_AIRLINES = ["ek", "ba", "ai"]
REQUEST_DELAY_SECONDS = 1.0
USER_AGENT = (
    "Mozilla/5.0 (compatible; FlightBenchmarking/0.1; +https://github.com/emirates/flight-benchmarking)"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_HTML_DIR = PROJECT_ROOT / "data" / "raw"
PARSED_DIR = PROJECT_ROOT / "data" / "parsed"

AIRLINE_NAMES: dict[str, str] = {
    "ek": "Emirates",
    "ba": "British Airways",
    "ai": "Air India",
}
