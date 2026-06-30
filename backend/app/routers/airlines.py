"""Airline summary endpoints."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.entities import AircraftConfiguration, Airline
from backend.app.routers.aircraft_grouping import config_group_id
from shared.schemas import AirlineSummary


def get_airline_summaries(db: Session) -> list[AirlineSummary]:
    summaries: list[AirlineSummary] = []
    airlines = db.query(Airline).order_by(Airline.name).all()
    for airline in airlines:
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
        summaries.append(
            AirlineSummary(
                slug=airline.slug,
                iata_code=airline.iata_code,
                name=airline.name,
                config_count=len(group_ids),
                total_fleet_seats=total_seats,
                aircraft_types=types,
                last_pipeline_update=last_update,
            )
        )
    return summaries
