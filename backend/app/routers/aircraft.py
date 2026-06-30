"""Aircraft list and detail endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from backend.app.models.entities import AircraftConfiguration, Airline, CabinConfiguration
from backend.app.routers.aircraft_grouping import (
    _cabins_from_entity,
    _decks_for_record,
    _pick_primary,
    group_aircraft_rows,
    merge_detail_records,
    merge_list_items,
)
from shared.compare_fields import AIRCRAFT_FIELDS, CABIN_FIELDS, coerce_field_value
from shared.schemas import AircraftConfigUpdate
from shared.schemas import AircraftConfiguration as AircraftSchema
from shared.schemas import AircraftListItem, SeatCounts, SeatRatingSummary, WifiInfo

CABIN_TYPE_BY_KEY = {
    "first": "F",
    "business": "J",
    "premium_economy": "W",
    "economy": "M",
}


def list_aircraft(
  db: Session,
  airline: str | None = None,
  aircraft_type: str | None = None,
  search: str | None = None,
  offset: int = 0,
  limit: int = 100,
) -> tuple[list[AircraftListItem], int]:
  query = (
    db.query(AircraftConfiguration, Airline)
    .join(Airline, AircraftConfiguration.airline_id == Airline.id)
  )
  if airline:
    query = query.filter(Airline.slug == airline)
  if aircraft_type:
    query = query.filter(AircraftConfiguration.aircraft_type_displayed.ilike(f"%{aircraft_type}%"))
  if search:
    group_id = func.coalesce(AircraftConfiguration.parent_svg_id, AircraftConfiguration.svg_id)
    query = query.filter(
      or_(
        group_id.ilike(f"%{search}%"),
        AircraftConfiguration.aircraft_code_displayed.ilike(f"%{search}%"),
        AircraftConfiguration.aircraft_type_displayed.ilike(f"%{search}%"),
        AircraftConfiguration.configuration.ilike(f"%{search}%"),
      )
    )

  rows = query.all()
  grouped = group_aircraft_rows(rows)
  total = len(grouped)
  page = grouped[offset : offset + limit]
  items = [merge_list_items(members) for _, members in page]
  return items, total


def _detail_from_entity(ac: AircraftConfiguration) -> AircraftSchema:
  cabins = {c.cabin_key: _cabins_from_entity(c) for c in ac.cabins}
  decks = _decks_for_record(ac)

  return AircraftSchema(
    svg_id=ac.svg_id,
    airline_iata=ac.airline.iata_code or ac.airline.slug.upper(),
    airline_name=ac.airline.name,
    iata_code=ac.iata_code,
    aircraft_type=ac.aircraft_type,
    aircraft_type_displayed=ac.aircraft_type_displayed,
    aircraft_code_displayed=ac.aircraft_code_displayed,
    manufacturer=ac.manufacturer,
    haul_type=ac.haul_type,
    lifecycle=ac.lifecycle,
    is_dual_deck=ac.is_dual_deck,
    deck=ac.deck,
    parent_svg_id=ac.parent_svg_id,
    deck_state=ac.deck_state,
    fleet_count=ac.fleet_count,
    last_updated=ac.last_updated,
    configuration=ac.configuration,
    description=ac.description,
    total_seats=ac.total_seats,
    seat_counts=SeatCounts(**ac.seat_counts) if ac.seat_counts else None,
    ife_provider=ac.ife_provider,
    ife_system_name=ac.ife_system_name,
    ife_description=ac.ife_description,
    wifi_provider=ac.wifi_provider,
    wifi_system_name=ac.wifi_system_name,
    wifi=WifiInfo(**ac.wifi) if ac.wifi else None,
    seat_rating_summary=SeatRatingSummary(**ac.seat_rating_summary) if ac.seat_rating_summary else None,
    decks=decks,
    cabins=cabins,
  )


def get_aircraft_detail(db: Session, svg_id: str) -> AircraftSchema | None:
  ac = (
    db.query(AircraftConfiguration)
    .options(joinedload(AircraftConfiguration.cabins), joinedload(AircraftConfiguration.airline))
    .filter(AircraftConfiguration.svg_id == svg_id)
    .first()
  )
  if ac:
    return _detail_from_entity(ac)

  members = (
    db.query(AircraftConfiguration)
    .options(joinedload(AircraftConfiguration.cabins), joinedload(AircraftConfiguration.airline))
    .filter(AircraftConfiguration.parent_svg_id == svg_id)
    .all()
  )
  if not members:
    return None

  return merge_detail_records(members)


def _resolve_group_members(db: Session, svg_id: str) -> list[AircraftConfiguration]:
    direct = (
        db.query(AircraftConfiguration)
        .options(joinedload(AircraftConfiguration.cabins), joinedload(AircraftConfiguration.airline))
        .filter(AircraftConfiguration.svg_id == svg_id)
        .first()
    )
    if direct:
        return [direct]

    return (
        db.query(AircraftConfiguration)
        .options(joinedload(AircraftConfiguration.cabins), joinedload(AircraftConfiguration.airline))
        .filter(AircraftConfiguration.parent_svg_id == svg_id)
        .all()
    )


def _find_cabin_owner(members: list[AircraftConfiguration], cabin_key: str) -> AircraftConfiguration:
    best_ac: AircraftConfiguration | None = None
    best_seats = -1
    for ac in members:
        for cabin in ac.cabins:
            if cabin.cabin_key == cabin_key:
                seats = cabin.num_seats or 0
                if seats > best_seats:
                    best_seats = seats
                    best_ac = ac
    if best_ac is None:
        return _pick_primary(members)
    return best_ac


def _get_or_create_cabin_row(
    db: Session,
    owner: AircraftConfiguration,
    cabin_key: str,
) -> CabinConfiguration:
    cabin_row = next((c for c in owner.cabins if c.cabin_key == cabin_key), None)
    if cabin_row is not None:
        return cabin_row

    cabin_row = CabinConfiguration(
        aircraft_id=owner.id,
        deck=owner.deck,
        cabin_key=cabin_key,
        cabin_type=CABIN_TYPE_BY_KEY.get(cabin_key, ""),
        cabin_class=cabin_key.replace("_", " ").title(),
        num_seats=0,
    )
    owner.cabins.append(cabin_row)
    db.add(cabin_row)
    db.flush()
    return cabin_row


def update_aircraft_config(
    db: Session,
    svg_id: str,
    update: AircraftConfigUpdate,
) -> AircraftSchema:
    if not update.aircraft and not update.cabins:
        raise ValueError("At least one aircraft or cabin field must be provided")

    members = _resolve_group_members(db, svg_id)
    if not members:
        raise LookupError(f"Aircraft configuration not found: {svg_id}")

    primary = _pick_primary(members)
    now = datetime.now(timezone.utc)

    for field_key, raw_value in update.aircraft.items():
        if field_key not in AIRCRAFT_FIELDS:
            raise ValueError(f"Unknown aircraft field: {field_key}")
        setattr(primary, field_key, coerce_field_value(field_key, raw_value))

    if update.aircraft:
        primary.updated_at = now

    for cabin_key, cabin_fields in update.cabins.items():
        if not cabin_fields:
            continue
        owner = _find_cabin_owner(members, cabin_key) if len(members) > 1 else primary
        cabin_row = _get_or_create_cabin_row(db, owner, cabin_key)
        for field_key, raw_value in cabin_fields.items():
            if field_key not in CABIN_FIELDS:
                raise ValueError(f"Unknown cabin field: {field_key}")
            setattr(cabin_row, field_key, coerce_field_value(field_key, raw_value))

    db.flush()
    return get_aircraft_detail(db, svg_id) or _detail_from_entity(primary)
