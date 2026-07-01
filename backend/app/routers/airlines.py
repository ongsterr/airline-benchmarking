"""Airline summary endpoints."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.entities import AircraftConfiguration, Airline
from backend.app.routers.aircraft_grouping import _pick_primary, config_group_id
from shared.constants import is_display_airline_slug
from shared.schemas import AirlineSummary


def _count_config_groups(configs: list[AircraftConfiguration]) -> tuple[int, int, int, int, int]:
    groups: dict[str, list[AircraftConfiguration]] = defaultdict(list)
    for config in configs:
        groups[config_group_id(config)].append(config)

    long_haul_count = 0
    short_haul_count = 0
    airbus_count = 0
    boeing_count = 0
    other_aircraft_count = 0

    for members in groups.values():
        primary = _pick_primary(members)
        haul = (primary.haul_type or "").lower()
        if "long" in haul:
            long_haul_count += 1
        elif "short" in haul:
            short_haul_count += 1

        manufacturer = (primary.manufacturer or "").lower()
        if manufacturer == "airbus":
            airbus_count += 1
        elif manufacturer == "boeing":
            boeing_count += 1
        else:
            other_aircraft_count += 1

    return long_haul_count, short_haul_count, airbus_count, boeing_count, other_aircraft_count


def get_airline_summaries(db: Session) -> list[AirlineSummary]:
    summaries: list[AirlineSummary] = []
    airlines = db.query(Airline).order_by(Airline.name).all()
    for airline in airlines:
        if not is_display_airline_slug(airline.slug):
            continue
        configs = (
            db.query(AircraftConfiguration)
            .filter(AircraftConfiguration.airline_id == airline.id)
            .all()
        )
        group_ids = {config_group_id(c) for c in configs}
        types = sorted(
            {c.aircraft_type_displayed for c in configs if c.aircraft_type_displayed}
        )
        total_seats = sum((c.total_seats or 0) * (c.fleet_count or 1) for c in configs)
        last_update = (
            db.query(func.max(AircraftConfiguration.fetched_at))
            .filter(AircraftConfiguration.airline_id == airline.id)
            .scalar()
        )
        long_haul, short_haul, airbus, boeing, other = _count_config_groups(configs)
        summaries.append(
            AirlineSummary(
                slug=airline.slug,
                iata_code=airline.iata_code,
                name=airline.name,
                config_count=len(group_ids),
                total_fleet_seats=total_seats,
                aircraft_types=types,
                long_haul_count=long_haul,
                short_haul_count=short_haul,
                airbus_count=airbus,
                boeing_count=boeing,
                other_aircraft_count=other,
                last_pipeline_update=last_update,
            )
        )
    return summaries
