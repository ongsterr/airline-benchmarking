"""Verify dual-deck normalization and DB load for A380 configs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from backend.app.db.session import SessionLocal, init_schema
from pipeline.deck import is_dual_deck_parent
from pipeline.load import upsert_aircraft
from pipeline.normalize import normalize_with_llm
from shared.schemas import AircraftConfiguration

TARGETS = ("ek-388j", "ek-388j-m", "ek-388j-u")


def main() -> None:
    load_dotenv()
    init_schema()
    db = SessionLocal()
    fetched_at = datetime.now(timezone.utc)

    for svg_id in TARGETS:
        raw_path = Path(f"data/parsed/{svg_id}.raw.json")
        if not raw_path.exists():
            print(f"{svg_id}: missing raw artifact")
            continue

        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        if is_dual_deck_parent(svg_id, raw):
            print(f"{svg_id}: skipped parent (expected)")
            continue

        result = normalize_with_llm(raw, "ek", "Emirates")
        ac: AircraftConfiguration = result.aircraft
        upsert_aircraft(db, "ek", ac, fetched_at)
        db.commit()

        deck_cabins = ac.decks[ac.deck].cabins if ac.deck and ac.deck in ac.decks else ac.cabins
        rows = {k: v.rows for k, v in deck_cabins.items()}
        print(f"{svg_id}: deck={ac.deck} parent={ac.parent_svg_id} rows={rows}")

    db.close()


if __name__ == "__main__":
    main()
