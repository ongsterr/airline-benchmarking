"""Aircraft list and detail endpoints."""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from backend.app.models.entities import AircraftConfiguration, Airline
from backend.app.routers.aircraft_grouping import (
    _cabins_from_entity,
    _decks_for_record,
    config_group_id,
    group_aircraft_rows,
    merge_detail_records,
    merge_list_items,
)
from shared.schemas import AircraftConfiguration as AircraftSchema
from shared.schemas import AircraftListItem, SeatCounts, SeatRatingSummary, WifiInfo


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
