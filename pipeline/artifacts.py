"""Save pipeline parse/normalize artifacts for debugging."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pipeline.config import PARSED_DIR
from shared.schemas import AircraftConfiguration


def save_artifacts(
    svg_id: str,
    raw: dict[str, Any],
    normalized: AircraftConfiguration,
    source: str,
    llm_parsed: dict[str, Any] | None = None,
    dropped_fields: list[str] | None = None,
    cleaned_raw: dict[str, Any] | None = None,
) -> None:
    """Write raw, normalized, and meta JSON under data/parsed/."""
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = PARSED_DIR / f"{svg_id}.raw.json"
    raw_path.write_text(json.dumps(raw, indent=2, default=str), encoding="utf-8")

    if cleaned_raw is not None:
        cleaned_path = PARSED_DIR / f"{svg_id}.cleaned.json"
        cleaned_path.write_text(json.dumps(cleaned_raw, indent=2, default=str), encoding="utf-8")

    if llm_parsed is not None:
        llm_path = PARSED_DIR / f"{svg_id}.llm.json"
        llm_path.write_text(json.dumps(llm_parsed, indent=2, default=str), encoding="utf-8")

    normalized_path = PARSED_DIR / f"{svg_id}.normalized.json"
    normalized_path.write_text(
        json.dumps(normalized.model_dump(mode="json"), indent=2, default=str),
        encoding="utf-8",
    )

    meta = {
        "svg_id": svg_id,
        "source": source,
        "normalized_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": str(normalized.last_updated) if normalized.last_updated else None,
        "dropped_fields": dropped_fields or [],
    }
    meta_path = PARSED_DIR / f"{svg_id}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
