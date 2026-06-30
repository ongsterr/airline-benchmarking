"""Save flight pipeline artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.flight_config import FLIGHT_PARSED_DIR


def save_flight_artifacts(
    slug: str,
    features: dict[str, Any],
    source: str,
    *,
    llm_parsed: dict[str, Any] | None = None,
    research_model: str | None = None,
    researched_at: datetime | None = None,
    sources_by_cabin: dict[str, list[dict[str, Any]]] | None = None,
    grounding_queries: list[str] | None = None,
) -> None:
    FLIGHT_PARSED_DIR.mkdir(parents=True, exist_ok=True)
    base = FLIGHT_PARSED_DIR / slug
    ts = researched_at or datetime.now(timezone.utc)
    base.with_suffix(".extracted.json").write_text(
        json.dumps(features, indent=2, default=str), encoding="utf-8"
    )
    meta: dict[str, Any] = {
        "source": source,
        "research_model": research_model,
        "researched_at": ts.isoformat(),
    }
    if sources_by_cabin:
        meta["sources_by_cabin"] = sources_by_cabin
    if grounding_queries:
        meta["grounding_queries"] = grounding_queries
    if llm_parsed:
        base.with_suffix(".llm.json").write_text(
            json.dumps(llm_parsed, indent=2, default=str), encoding="utf-8"
        )
    base.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
