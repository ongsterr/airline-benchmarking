"""Discover aircraft configuration URLs from AeroLOPA airline pages."""

from __future__ import annotations

import re

import httpx

from pipeline.config import AIRLINE_NAMES, BASE_URL, USER_AGENT
from pipeline.parse_json import extract_aircraft_codes_from_html


def discover_configs_for_airline(slug: str, client: httpx.Client | None = None) -> list[str]:
    """Return unique svg_ids (e.g. ek-359g) for an airline slug."""
    url = f"{BASE_URL}/{slug}"
    own_client = client is None
    if own_client:
        client = httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30)

    try:
        response = client.get(url)
        response.raise_for_status()
        html = response.text
    finally:
        if own_client:
            client.close()

    href_pattern = re.compile(rf'href="/{re.escape(slug)}-[^"]+"')
    hrefs = {m.group(0).split('"')[1].lstrip("/") for m in href_pattern.finditer(html)}
    json_codes = set(extract_aircraft_codes_from_html(html, slug))
    return sorted(hrefs | json_codes)


def discover_all(airline_slugs: list[str]) -> dict[str, list[str]]:
    """Discover configs for multiple airlines."""
    results: dict[str, list[str]] = {}
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30) as client:
        for slug in airline_slugs:
            results[slug] = discover_configs_for_airline(slug, client)
    return results


def airline_display_name(slug: str) -> str:
    return AIRLINE_NAMES.get(slug, slug.upper())
