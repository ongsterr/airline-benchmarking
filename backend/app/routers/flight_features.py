"""Flight feature lookups and airline-level compare."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.entities import Airline, AirlineCabinFlightFeature
from shared.flight_fields import (
    FLIGHT_FIELDS,
    coerce_flight_field_value,
    field_label,
    format_flight_value,
)
from shared.schemas import (
    AirlineFlightFeatures,
    AirlineFlightFeaturesUpdate,
    CabinFlightFeatures,
    CompareAirlineColumn,
    CompareAirlineResponse,
    CompareRow,
)


def _entity_to_cabin(entity: AirlineCabinFlightFeature) -> CabinFlightFeatures:
    return CabinFlightFeatures(
        cabin_class=entity.cabin_class or entity.cabin_key.replace("_", " ").title(),
        check_in_priority=entity.check_in_priority,
        cabin_bag_pieces=entity.cabin_bag_pieces,
        cabin_bag_kg_per_piece=entity.cabin_bag_kg_per_piece,
        cabin_bag_kg_total=entity.cabin_bag_kg_total,
        checked_bag_pieces=entity.checked_bag_pieces,
        checked_bag_kg_per_piece=entity.checked_bag_kg_per_piece,
        checked_bag_kg_total=entity.checked_bag_kg_total,
        boarding_priority=entity.boarding_priority,
        lounge_access=entity.lounge_access,
        amenity_kit=entity.amenity_kit,
        amenity_kit_brand=entity.amenity_kit_brand,
        extra_features=entity.extra_features or {},
    )


def _cabin_entities_for_slugs(
    db: Session,
    slugs: list[str],
    cabin_key: str,
) -> dict[str, AirlineCabinFlightFeature | None]:
    if not slugs:
        return {}
    airlines = db.query(Airline).filter(Airline.slug.in_(slugs)).all()
    slug_by_id = {airline.id: airline.slug for airline in airlines}
    if not slug_by_id:
        return {slug: None for slug in slugs}

    rows = (
        db.query(AirlineCabinFlightFeature)
        .filter(
            AirlineCabinFlightFeature.airline_id.in_(slug_by_id.keys()),
            AirlineCabinFlightFeature.cabin_key == cabin_key,
        )
        .all()
    )
    by_slug: dict[str, AirlineCabinFlightFeature | None] = {slug: None for slug in slugs}
    for row in rows:
        slug = slug_by_id.get(row.airline_id)
        if slug:
            by_slug[slug] = row
    return by_slug


def get_flight_features_for_slug(db: Session, slug: str) -> AirlineFlightFeatures | None:
    airline = db.query(Airline).filter(Airline.slug == slug).first()
    if not airline:
        return None
    rows = (
        db.query(AirlineCabinFlightFeature)
        .filter(AirlineCabinFlightFeature.airline_id == airline.id)
        .all()
    )
    if not rows:
        return None
    cabins = {row.cabin_key: _entity_to_cabin(row) for row in rows}
    return AirlineFlightFeatures(cabins=cabins)


def get_flight_features_by_slugs(db: Session, slugs: list[str]) -> dict[str, AirlineFlightFeatures]:
    if not slugs:
        return {}
    airlines = db.query(Airline).filter(Airline.slug.in_(slugs)).all()
    airline_ids = {a.id: a.slug for a in airlines}
    if not airline_ids:
        return {}

    rows = (
        db.query(AirlineCabinFlightFeature)
        .filter(AirlineCabinFlightFeature.airline_id.in_(airline_ids.keys()))
        .all()
    )
    result: dict[str, AirlineFlightFeatures] = {slug: AirlineFlightFeatures() for slug in slugs}
    for row in rows:
        slug = airline_ids.get(row.airline_id)
        if not slug:
            continue
        result[slug].cabins[row.cabin_key] = _entity_to_cabin(row)
    return result


def _flight_value_for_slug(
    flight_by_slug: dict[str, AirlineFlightFeatures],
    airline_slug: str,
    cabin_key: str,
    field: str,
) -> Any:
    features = flight_by_slug.get(airline_slug)
    if not features:
        return None
    cabin = features.cabins.get(cabin_key)
    if not cabin:
        return None
    return getattr(cabin, field, None)


def build_flight_compare_rows(
    configs: list,
    cabin_key: str,
    flight_by_slug: dict[str, AirlineFlightFeatures],
) -> list[CompareRow]:
    rows: list[CompareRow] = []
    for field in FLIGHT_FIELDS:
        rows.append(
            CompareRow(
                feature=field_label(field),
                field_key=field,
                scope="flight",
                category="Flight features",
                values={
                    config.svg_id: format_flight_value(
                        _flight_value_for_slug(
                            flight_by_slug, config.svg_id.split("-", 1)[0], cabin_key, field
                        )
                    )
                    for config in configs
                },
            )
        )
    return rows


def compare_airlines(
    db: Session,
    slugs: list[str],
    cabin: str | None = None,
) -> CompareAirlineResponse:
    cabin_key = (cabin or "business").lower().replace(" ", "_")
    category = f"Flight features ({cabin_key.replace('_', ' ').title()})"
    airlines = db.query(Airline).filter(Airline.slug.in_(slugs)).all()
    airline_by_slug = {a.slug: a for a in airlines}
    flight_by_slug = get_flight_features_by_slugs(db, slugs)
    cabin_entities = _cabin_entities_for_slugs(db, slugs, cabin_key)

    columns = [
        CompareAirlineColumn(
            slug=slug,
            iata_code=airline_by_slug[slug].iata_code,
            name=airline_by_slug[slug].name,
        )
        for slug in slugs
        if slug in airline_by_slug
    ]

    rows: list[CompareRow] = []
    for field in FLIGHT_FIELDS:
        rows.append(
            CompareRow(
                feature=field_label(field),
                field_key=field,
                scope="flight",
                category=category,
                values={
                    slug: format_flight_value(
                        _flight_value_for_slug(flight_by_slug, slug, cabin_key, field)
                    )
                    for slug in slugs
                },
            )
        )

    rows.append(
        CompareRow(
            feature="Reference URL",
            field_key="source_url",
            scope="flight",
            category=category,
            values={
                slug: format_flight_value(
                    cabin_entities[slug].source_url if cabin_entities.get(slug) else None
                )
                for slug in slugs
            },
        )
    )

    return CompareAirlineResponse(columns=columns, rows=rows)


def update_airline_cabin_flight_features(
    db: Session,
    slug: str,
    cabin_key: str,
    update: AirlineFlightFeaturesUpdate,
    *,
    update_source_url: bool = False,
) -> CabinFlightFeatures:
    airline = db.query(Airline).filter(Airline.slug == slug).first()
    if not airline:
        raise LookupError(f"Airline not found: {slug}")

    entity = (
        db.query(AirlineCabinFlightFeature)
        .filter(
            AirlineCabinFlightFeature.airline_id == airline.id,
            AirlineCabinFlightFeature.cabin_key == cabin_key,
        )
        .first()
    )
    if not entity:
        raise LookupError(f"Flight features not found for {slug} cabin {cabin_key}")

    if not update.fields and not update_source_url:
        raise ValueError("At least one field must be provided")

    for field_key, raw_value in update.fields.items():
        if field_key not in FLIGHT_FIELDS:
            raise ValueError(f"Unknown flight field: {field_key}")
        setattr(entity, field_key, coerce_flight_field_value(field_key, raw_value))

    if update_source_url:
        entity.source_url = update.source_url or None

    entity.updated_at = datetime.now(timezone.utc)
    db.flush()
    return _entity_to_cabin(entity)
