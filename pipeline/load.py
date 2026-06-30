"""Upsert normalized aircraft data into Postgres."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.models.entities import Airline, AircraftConfiguration, CabinConfiguration
from pipeline.config import BASE_URL
from shared.schemas import AircraftConfiguration as AircraftSchema


def get_existing_svg_ids(db: Session, svg_ids: list[str]) -> set[str]:
    if not svg_ids:
        return set()
    rows = (
        db.query(AircraftConfiguration.svg_id)
        .filter(AircraftConfiguration.svg_id.in_(svg_ids))
        .all()
    )
    return {row[0] for row in rows}


def get_or_create_airline(db: Session, slug: str, name: str, iata_code: str | None) -> Airline:
    airline = db.query(Airline).filter(Airline.slug == slug).first()
    if airline:
        airline.name = name
        if iata_code:
            airline.iata_code = iata_code
        return airline
    airline = Airline(slug=slug, name=name, iata_code=iata_code)
    db.add(airline)
    db.flush()
    return airline


def upsert_aircraft(
    db: Session,
    slug: str,
    data: AircraftSchema,
    fetched_at: datetime | None = None,
) -> AircraftConfiguration:
    """Upsert aircraft and cabins. Always writes extracted data to the database."""
    airline = get_or_create_airline(db, slug, data.airline_name, data.airline_iata)
    existing = db.query(AircraftConfiguration).filter(AircraftConfiguration.svg_id == data.svg_id).first()

    now = fetched_at or datetime.now(timezone.utc)
    wifi_dict = data.wifi.model_dump() if data.wifi else None
    seat_counts_dict = data.seat_counts.model_dump() if data.seat_counts else None
    rating_dict = data.seat_rating_summary.model_dump() if data.seat_rating_summary else None
    decks_dict = (
        {key: deck.model_dump(mode="json") for key, deck in data.decks.items()}
        if data.decks
        else None
    )

    fields = {
        "airline_id": airline.id,
        "source_url": f"{BASE_URL}/{data.svg_id}",
        "iata_code": data.iata_code,
        "aircraft_type": data.aircraft_type,
        "aircraft_type_displayed": data.aircraft_type_displayed,
        "aircraft_code_displayed": data.aircraft_code_displayed,
        "manufacturer": data.manufacturer,
        "haul_type": data.haul_type,
        "lifecycle": data.lifecycle,
        "is_dual_deck": data.is_dual_deck,
        "deck": data.deck,
        "parent_svg_id": data.parent_svg_id,
        "deck_state": data.deck_state,
        "decks": decks_dict,
        "fleet_count": data.fleet_count,
        "last_updated": data.last_updated,
        "configuration": data.configuration,
        "description": data.description,
        "total_seats": data.total_seats,
        "seat_counts": seat_counts_dict,
        "ife_provider": data.ife_provider,
        "ife_system_name": data.ife_system_name,
        "ife_description": data.ife_description,
        "wifi_provider": data.wifi_provider,
        "wifi_system_name": data.wifi_system_name,
        "wifi": wifi_dict,
        "seat_rating_summary": rating_dict,
        "fetched_at": now,
        "updated_at": now,
    }

    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
        aircraft = existing
        db.query(CabinConfiguration).filter(CabinConfiguration.aircraft_id == aircraft.id).delete()
    else:
        aircraft = AircraftConfiguration(svg_id=data.svg_id, created_at=now, **fields)
        db.add(aircraft)
        db.flush()

    cabin_source = data.cabins
    if data.deck and data.decks.get(data.deck):
        cabin_source = data.decks[data.deck].cabins or data.cabins

    for cabin_key, cabin in cabin_source.items():
        db.add(
            CabinConfiguration(
                aircraft_id=aircraft.id,
                deck=data.deck,
                cabin_key=cabin_key,
                cabin_type=cabin.cabin_type,
                cabin_class=cabin.cabin_class,
                num_seats=cabin.num_seats,
                rows=cabin.rows,
                row_start=cabin.row_start,
                row_end=cabin.row_end,
                layout=cabin.layout,
                seat_manufacturer=cabin.seat_manufacturer,
                pitch_inch=cabin.pitch_inch,
                width_inch=cabin.width_inch,
                recline_inch=cabin.recline_inch,
                recline_deg=cabin.recline_deg,
                has_flat_bed=cabin.has_flat_bed,
                bed_flat_length_inch=cabin.bed_flat_length_inch,
                screen_size_inch=cabin.screen_size_inch,
                screen_description=cabin.screen_description,
                ife_provider=cabin.ife_provider,
                ife_system_name=cabin.ife_system_name,
                ife=cabin.ife,
                wifi_provider=cabin.wifi_provider,
                wifi_system_name=cabin.wifi_system_name,
                wifi_description=cabin.wifi_description,
                power_v=cabin.power_v,
                power_description=cabin.power_description,
                usb_a_availability=cabin.usb_a_availability,
                usb_a_count=cabin.usb_a_count,
                usb_c_availability=cabin.usb_c_availability,
                usb_c_count=cabin.usb_c_count,
                usb_description=cabin.usb_description,
                bluetooth_connectivity=cabin.bluetooth_connectivity,
                wireless_charging=cabin.wireless_charging,
                privacy_doors=cabin.privacy_doors,
                personal_gasper_vent=cabin.personal_gasper_vent,
                adjustable_headrest=cabin.adjustable_headrest,
                adjustable_headrest_description=cabin.adjustable_headrest_description,
                adjustable_armrests=cabin.adjustable_armrests,
                adjustable_armrests_description=cabin.adjustable_armrests_description,
                direct_aisle_access_pct=cabin.direct_aisle_access_pct,
                seat_description=cabin.seat_description,
            )
        )

    db.flush()
    return aircraft
