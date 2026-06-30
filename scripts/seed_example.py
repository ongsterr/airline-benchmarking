"""Seed database from output.py example data (no network required)."""

from __future__ import annotations

from datetime import date

from dotenv import load_dotenv

from backend.app.db.session import SessionLocal, engine, init_schema
from backend.app.models.entities import Base
from pipeline.load import upsert_aircraft
from shared.schemas import (
    AircraftConfiguration,
    CabinConfiguration,
    SeatCounts,
    SeatRatingSummary,
    WifiInfo,
)

EXAMPLE = AircraftConfiguration(
    svg_id="ek-359g",
    airline_iata="EK",
    airline_name="Emirates",
    iata_code="359",
    aircraft_type="Airbus A350-941",
    aircraft_type_displayed="Airbus A350-900",
    aircraft_code_displayed="359G",
    manufacturer="Airbus",
    haul_type="Long Haul",
    lifecycle="active",
    is_dual_deck=False,
    fleet_count=13,
    last_updated=date(2026, 4, 8),
    configuration="32J 21W 259M",
    description="This version of the Emirates Airbus A350-900 is arranged in a 32J 21W 259M configuration",
    total_seats=312,
    seat_counts=SeatCounts(first=0, business=32, premium_economy=21, economy=259, total=312),
    ife_provider="Thales",
    ife_system_name="Avant",
    ife_description="Thales Avant system screening audio visual content gate to gate",
    wifi_provider="Viasat",
    wifi_system_name="Global Xpress",
    wifi=WifiInfo(technology="Inmarsat GX Aviation", tier=2, rating="Better", fleet_pct=100),
    seat_rating_summary=SeatRatingSummary(
        rated_seat_count=312, green_count=32, yellow_count=23, red_count=35
    ),
    cabins={
        "business": CabinConfiguration(
            cabin_type="J",
            cabin_class="Business",
            num_seats=32,
            rows="01 to 08",
            row_start=1,
            row_end=8,
            layout="1-2-1",
            seat_manufacturer="Safran",
            pitch_inch=44,
            width_inch=20.7,
            recline_deg=180,
            has_flat_bed=True,
            bed_flat_length_inch=78.6,
            screen_size_inch=23,
            screen_description='23" 4K UHD touch screen display',
            ife_provider="Thales",
            ife_system_name="Avant",
            power_v=110,
            usb_a_availability=True,
            usb_a_count=1,
            usb_c_availability=True,
            usb_c_count=2,
            direct_aisle_access_pct=100,
        ),
        "premium_economy": CabinConfiguration(
            cabin_type="W",
            cabin_class="Premium Economy",
            num_seats=21,
            rows="14 to 16",
            row_start=14,
            row_end=16,
            layout="2-3-2",
            seat_manufacturer="Recaro",
            pitch_inch=40,
            width_inch=19.5,
            recline_inch=8,
            screen_size_inch=13.3,
            power_v=110,
            usb_a_availability=True,
            usb_a_count=1,
            usb_c_availability=True,
            usb_c_count=1,
        ),
        "economy": CabinConfiguration(
            cabin_type="M",
            cabin_class="Economy",
            num_seats=259,
            rows="19 to 47",
            row_start=19,
            row_end=47,
            layout="3-3-3",
            seat_manufacturer="Safran",
            pitch_inch=32,
            width_inch=18,
            recline_inch=6,
            screen_size_inch=13.3,
            usb_a_availability=True,
            usb_a_count=1,
            usb_c_availability=True,
            usb_c_count=1,
        ),
    },
)


def main() -> None:
    load_dotenv()
    init_schema()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    upsert_aircraft(db, "ek", EXAMPLE)
    db.commit()
    db.close()
    print("Seeded ek-359g example data.")


if __name__ == "__main__":
    main()
