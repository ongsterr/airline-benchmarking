"""Aircraft comparison endpoint."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.routers.aircraft import get_aircraft_detail
from pipeline.config import BASE_URL
from shared.compare_fields import AIRCRAFT_FIELDS, CABIN_FIELDS, field_label
from shared.schemas import CompareConfigColumn, CompareResponse, CompareRow


def _config_column(detail) -> CompareConfigColumn:
    airline_slug = detail.svg_id.split("-", 1)[0]
    return CompareConfigColumn(
        svg_id=detail.svg_id,
        airline_slug=airline_slug,
        airline_name=detail.airline_name,
        aircraft_type_displayed=detail.aircraft_type_displayed,
        aircraft_code_displayed=detail.aircraft_code_displayed,
        configuration=detail.configuration,
        source_url=f"{BASE_URL}/{detail.svg_id}",
    )


def compare_aircraft(
    db: Session,
    svg_ids: list[str],
    cabin: str | None = None,
) -> CompareResponse:
    configs = []
    for svg_id in svg_ids:
        detail = get_aircraft_detail(db, svg_id)
        if detail:
            configs.append(detail)

    if not configs:
        return CompareResponse(columns=[], rows=[])

    rows: list[CompareRow] = []

    for field in AIRCRAFT_FIELDS:
        rows.append(
            CompareRow(
                feature=field_label(field),
                field_key=field,
                scope="aircraft",
                category="Aircraft",
                values={c.svg_id: getattr(c, field, None) for c in configs},
            )
        )

    cabin_key = (cabin or "business").lower().replace(" ", "_")
    for field in CABIN_FIELDS:
        rows.append(
            CompareRow(
                feature=field_label(field),
                field_key=field,
                scope="cabin",
                category=f"Cabin ({cabin_key.replace('_', ' ').title()})",
                values={
                    c.svg_id: (
                        getattr(c.cabins.get(cabin_key), field, None)
                        if c.cabins.get(cabin_key)
                        else None
                    )
                    for c in configs
                },
            )
        )

    return CompareResponse(
        columns=[_config_column(c) for c in configs],
        rows=rows,
    )
