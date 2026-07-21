"""Fetch Emirates digital-menu JSON via public API (page HTML is JS-only shell)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from pipeline.config import REQUEST_DELAY_SECONDS, USER_AGENT
from pipeline.menu_config import (
    MENU_API_LANG,
    MENU_API_URL,
    MENU_BASE_URL,
    MENU_CABIN_CODES,
    MENU_EVIDENCE_DIR,
    MENU_RAW_DIR,
    MENU_URL_TEMPLATE,
    format_api_scheduled_date,
)


@dataclass
class MenuFetchResult:
    cabin_norm: str
    cabin_code: str
    source_url: str
    api_url: str
    status_code: int
    html: str | None = None
    api_payload: dict[str, Any] | None = None
    snapshot_path: Path | None = None
    raw_bytes_size: int | None = None
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    empty_or_missing: bool = False


def build_menu_url(
    service_date: date,
    flight: str,
    origin: str,
    destination: str,
    cabin_norm: str,
) -> tuple[str, str]:
    """Return (cabin_code, page url) for a cabin (audit / Referer)."""
    cabin_code = MENU_CABIN_CODES[cabin_norm]
    flight_num = flight.lstrip("0") or flight
    url = MENU_URL_TEMPLATE.format(
        base=MENU_BASE_URL.rstrip("/") + "/",
        date=service_date.isoformat(),
        flight=flight_num,
        origin=origin.upper(),
        destination=destination.upper(),
        cabin_code=cabin_code,
    )
    return cabin_code, url


def build_api_payload(
    service_date: date,
    flight: str,
    origin: str,
    cabin_norm: str,
) -> dict[str, Any]:
    cabin_code = MENU_CABIN_CODES[cabin_norm]
    flight_num = flight.lstrip("0") or flight
    return {
        "flightNumber": flight_num,
        "departureStation": origin.upper(),
        "scheduledDate": format_api_scheduled_date(service_date),
        "cabinClass": cabin_code.upper(),
        "isPaxMeal": False,
        "isDigitalMenuWithPaxMeal": "",
    }


def _snapshot_stem(
    service_date: date,
    flight: str,
    origin: str,
    destination: str,
    cabin_code: str,
) -> str:
    flight_safe = flight.replace(" ", "").lower()
    return (
        f"{origin.lower()}_{destination.lower()}_"
        f"{flight_safe}_{service_date.isoformat()}_{cabin_code}"
    )


def _count_items(payload: dict[str, Any] | None) -> int:
    if not payload:
        return 0
    total = 0
    for cat in payload.get("categories") or []:
        if not isinstance(cat, dict):
            continue
        for sub in cat.get("subCategories") or []:
            if isinstance(sub, dict):
                total += len(sub.get("items") or [])
    return total


def fetch_menu_api(
    service_date: date,
    flight: str,
    origin: str,
    destination: str,
    cabin_norm: str,
    client: httpx.Client | None = None,
    *,
    lang: str = MENU_API_LANG,
) -> MenuFetchResult:
    """POST digital-menu API and save JSON evidence snapshot."""
    cabin_code, page_url = build_menu_url(
        service_date, flight, origin, destination, cabin_norm
    )
    api_url = f"{MENU_API_URL}?lang={lang}"
    payload = build_api_payload(service_date, flight, origin, cabin_norm)
    captured_at = datetime.now(timezone.utc)
    owns_client = client is None
    if owns_client:
        client = httpx.Client(
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": "https://www.emirates.com",
            },
            follow_redirects=True,
            timeout=45,
        )

    try:
        assert client is not None
        headers = {"Referer": page_url}
        response = client.post(api_url, json=payload, headers=headers)
        raw_text = response.text
        raw_bytes = len(raw_text.encode("utf-8"))

        api_data: dict[str, Any] | None = None
        empty_or_missing = response.status_code != 200
        try:
            parsed = response.json()
            if isinstance(parsed, dict):
                api_data = parsed
                if _count_items(api_data) == 0 and not (api_data.get("categories") or []):
                    empty_or_missing = True
            else:
                empty_or_missing = True
        except json.JSONDecodeError:
            empty_or_missing = True

        MENU_RAW_DIR.mkdir(parents=True, exist_ok=True)
        MENU_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        stem = _snapshot_stem(service_date, flight, origin, destination, cabin_code)
        evidence_path = MENU_EVIDENCE_DIR / f"{stem}.json"
        raw_path = MENU_RAW_DIR / f"{stem}.json"
        snapshot_body = json.dumps(api_data if api_data is not None else {"raw": raw_text}, indent=2, ensure_ascii=False)
        raw_path.write_text(snapshot_body, encoding="utf-8")
        evidence_path.write_text(snapshot_body, encoding="utf-8")

        return MenuFetchResult(
            cabin_norm=cabin_norm,
            cabin_code=cabin_code,
            source_url=page_url,
            api_url=api_url,
            status_code=response.status_code,
            api_payload=api_data,
            snapshot_path=evidence_path,
            raw_bytes_size=raw_bytes,
            captured_at=captured_at,
            empty_or_missing=empty_or_missing,
        )
    except httpx.HTTPError as exc:
        return MenuFetchResult(
            cabin_norm=cabin_norm,
            cabin_code=cabin_code,
            source_url=page_url,
            api_url=api_url,
            status_code=0,
            captured_at=captured_at,
            error=str(exc),
            empty_or_missing=True,
        )
    finally:
        if owns_client and client is not None:
            client.close()


# Back-compat alias used by older call sites
fetch_menu_html = fetch_menu_api


__all__ = [
    "MenuFetchResult",
    "REQUEST_DELAY_SECONDS",
    "build_api_payload",
    "build_menu_url",
    "fetch_menu_api",
    "fetch_menu_html",
]
