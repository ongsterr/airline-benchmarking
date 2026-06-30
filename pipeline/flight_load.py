"""Upsert airline cabin flight features into Postgres."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.models.entities import AirlineCabinFlightFeature, FlightFeatureSource
from pipeline.load import get_or_create_airline
from shared.schemas import AirlineFlightFeatures, CabinFlightFeatures, FlightSourceCandidate


def airline_has_flight_features(db: Session, slug: str) -> bool:
    from backend.app.models.entities import Airline

    airline = db.query(Airline).filter(Airline.slug == slug).first()
    if not airline:
        return False
    return (
        db.query(AirlineCabinFlightFeature)
        .filter(AirlineCabinFlightFeature.airline_id == airline.id)
        .count()
        > 0
    )


def upsert_flight_sources(
    db: Session,
    slug: str,
    airline_name: str,
    iata_code: str | None,
    sources: list[tuple[FlightSourceCandidate, int | None, datetime]],
) -> None:
    """sources: list of (candidate, http_status, fetched_at)"""
    airline = get_or_create_airline(db, slug, airline_name, iata_code)
    for candidate, http_status, fetched_at in sources:
        existing = (
            db.query(FlightFeatureSource)
            .filter(FlightFeatureSource.airline_id == airline.id, FlightFeatureSource.url == candidate.url)
            .first()
        )
        if existing:
            existing.source_type = candidate.source_type
            existing.page_type = candidate.page_type
            existing.cabin_keys = candidate.cabin_keys or None
            existing.title = candidate.title
            existing.http_status = http_status
            existing.fetched_at = fetched_at
        else:
            db.add(
                FlightFeatureSource(
                    airline_id=airline.id,
                    url=candidate.url,
                    source_type=candidate.source_type,
                    page_type=candidate.page_type,
                    cabin_keys=candidate.cabin_keys or None,
                    title=candidate.title,
                    http_status=http_status,
                    fetched_at=fetched_at,
                )
            )


def _upsert_cabin_row(
    db: Session,
    airline_id,
    cabin_key: str,
    cabin: CabinFlightFeatures,
    source_url: str | None,
    fetched_at: datetime,
) -> None:
    now = fetched_at
    existing = (
        db.query(AirlineCabinFlightFeature)
        .filter(
            AirlineCabinFlightFeature.airline_id == airline_id,
            AirlineCabinFlightFeature.cabin_key == cabin_key,
        )
        .first()
    )
    fields = {
        "cabin_class": cabin.cabin_class,
        "check_in_priority": cabin.check_in_priority,
        "cabin_bag_pieces": cabin.cabin_bag_pieces,
        "cabin_bag_kg_per_piece": cabin.cabin_bag_kg_per_piece,
        "cabin_bag_kg_total": cabin.cabin_bag_kg_total,
        "checked_bag_pieces": cabin.checked_bag_pieces,
        "checked_bag_kg_per_piece": cabin.checked_bag_kg_per_piece,
        "checked_bag_kg_total": cabin.checked_bag_kg_total,
        "boarding_priority": cabin.boarding_priority,
        "lounge_access": cabin.lounge_access,
        "amenity_kit": cabin.amenity_kit,
        "amenity_kit_brand": cabin.amenity_kit_brand,
        "extra_features": cabin.extra_features or None,
        "source_url": source_url,
        "fetched_at": fetched_at,
        "updated_at": now,
    }
    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
    else:
        db.add(
            AirlineCabinFlightFeature(
                airline_id=airline_id,
                cabin_key=cabin_key,
                **fields,
            )
        )


def upsert_flight_features(
    db: Session,
    slug: str,
    airline_name: str,
    iata_code: str | None,
    features: AirlineFlightFeatures,
    source_url: str | None,
    fetched_at: datetime | None = None,
) -> None:
    airline = get_or_create_airline(db, slug, airline_name, iata_code)
    ts = fetched_at or datetime.now(timezone.utc)
    for cabin_key, cabin in features.cabins.items():
        _upsert_cabin_row(db, airline.id, cabin_key, cabin, source_url, ts)
