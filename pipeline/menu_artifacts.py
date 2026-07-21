"""Save menu pipeline artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.menu_config import MENU_PARSED_DIR


def _artifact_stem(
    origin: str,
    destination: str,
    flight: str,
    service_date: str,
    cabin_code: str,
) -> str:
    flight_safe = flight.replace(" ", "").lower()
    return (
        f"{origin.lower()}_{destination.lower()}_"
        f"{flight_safe}_{service_date}_{cabin_code}"
    )


def save_menu_artifacts(
    *,
    origin: str,
    destination: str,
    flight: str,
    service_date: str,
    cabin_code: str,
    extraction: dict[str, Any],
    source: str,
    extractor_version: str | None = None,
    source_url: str | None = None,
    snapshot_path: str | None = None,
    extracted_at: datetime | None = None,
    llm_parsed: dict[str, Any] | None = None,
    enrichment_parsed: dict[str, Any] | None = None,
) -> Path:
    """Write .extracted.json / .meta.json (and optional .llm.json / .enrichment.json)."""
    MENU_PARSED_DIR.mkdir(parents=True, exist_ok=True)
    stem = _artifact_stem(origin, destination, flight, service_date, cabin_code)
    base = MENU_PARSED_DIR / stem
    ts = extracted_at or datetime.now(timezone.utc)

    base.with_suffix(".extracted.json").write_text(
        json.dumps(extraction, indent=2, default=str), encoding="utf-8"
    )
    if llm_parsed is not None:
        base.with_suffix(".llm.json").write_text(
            json.dumps(llm_parsed, indent=2, default=str), encoding="utf-8"
        )
    if enrichment_parsed is not None:
        base.with_suffix(".enrichment.json").write_text(
            json.dumps(enrichment_parsed, indent=2, default=str), encoding="utf-8"
        )

    meta: dict[str, Any] = {
        "source": source,
        "extractor_version": extractor_version,
        "extracted_at": ts.isoformat(),
        "source_url": source_url,
        "snapshot_path": snapshot_path,
        "origin": origin,
        "destination": destination,
        "flight": flight,
        "service_date": service_date,
        "cabin_code": cabin_code,
    }
    base.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return base
