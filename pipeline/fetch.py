"""Fetch and store raw HTML for aircraft configuration pages."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from pipeline.config import BASE_URL, RAW_HTML_DIR, REQUEST_DELAY_SECONDS, USER_AGENT


@dataclass
class FetchResult:
    svg_id: str
    status_code: int
    html_path: Path | None
    fetched_at: datetime
    error: str | None = None


def fetch_config_html(svg_id: str, client: httpx.Client) -> FetchResult:
    """Fetch a single config page and save raw HTML."""
    url = f"{BASE_URL}/{svg_id}"
    fetched_at = datetime.now(timezone.utc)
    try:
        response = client.get(url)
        RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
        path = RAW_HTML_DIR / f"{svg_id}.html"
        path.write_text(response.text, encoding="utf-8")
        return FetchResult(
            svg_id=svg_id,
            status_code=response.status_code,
            html_path=path,
            fetched_at=fetched_at,
        )
    except httpx.HTTPError as exc:
        return FetchResult(
            svg_id=svg_id,
            status_code=0,
            html_path=None,
            fetched_at=fetched_at,
            error=str(exc),
        )


def fetch_configs(svg_ids: list[str], delay: float = REQUEST_DELAY_SECONDS) -> list[FetchResult]:
    """Fetch multiple config pages with polite delay."""
    results: list[FetchResult] = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30) as client:
        for i, svg_id in enumerate(svg_ids):
            results.append(fetch_config_html(svg_id, client))
            if i < len(svg_ids) - 1:
                time.sleep(delay)
    return results


def load_cached_html(svg_id: str) -> str | None:
    path = RAW_HTML_DIR / f"{svg_id}.html"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None
