"""CSV export endpoint helpers for selected fleet configs."""

from __future__ import annotations

from csv import DictWriter
from datetime import date
from io import StringIO
from typing import Any

from sqlalchemy.orm import Session

from backend.app.routers.aircraft import get_aircraft_detail
from shared.compare_fields import AIRCRAFT_FIELDS, CABIN_FIELDS

STANDARD_CABIN_KEYS = ["first", "business", "premium_economy", "economy"]


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def build_csv_rows(svg_ids: list[str], db: Session) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for svg_id in svg_ids:
        config = get_aircraft_detail(db, svg_id)
        if not config:
            continue

        for cabin_key in STANDARD_CABIN_KEYS:
            cabin = config.cabins.get(cabin_key)
            if not cabin:
                continue

            row: dict[str, Any] = {
                "airline_name": config.airline_name,
                "svg_id": config.svg_id,
                "aircraft_type_displayed": config.aircraft_type_displayed,
                "aircraft_code_displayed": config.aircraft_code_displayed,
                "cabin_class": cabin.cabin_class,
                "cabin_key": cabin_key,
            }
            for field in AIRCRAFT_FIELDS:
                row[field] = _csv_value(getattr(config, field, None))
            for field in CABIN_FIELDS:
                row[field] = _csv_value(getattr(cabin, field, None))
            rows.append(row)

    rows.sort(
        key=lambda row: (
            str(row["airline_name"] or ""),
            str(row["svg_id"] or ""),
            STANDARD_CABIN_KEYS.index(row["cabin_key"]),
        )
    )
    return rows


def render_csv(rows: list[dict[str, Any]]) -> str:
    fieldnames = [
        "airline_name",
        "svg_id",
        "aircraft_type_displayed",
        "aircraft_code_displayed",
        "cabin_class",
        "cabin_key",
        *AIRCRAFT_FIELDS,
        *CABIN_FIELDS,
    ]

    output = StringIO()
    writer = DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def build_export_csv(svg_ids: list[str], db: Session) -> tuple[str, str]:
    rows = build_csv_rows(svg_ids, db)
    content = render_csv(rows)
    filename = f"fleet-export-{date.today().isoformat()}.csv"
    return content, filename
