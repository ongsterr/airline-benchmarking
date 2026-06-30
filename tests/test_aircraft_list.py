"""Tests for aircraft list endpoint filters."""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal, engine, init_schema
from backend.app.main import app
from backend.app.models.entities import Base
from pipeline.load import upsert_aircraft
from shared.schemas import AircraftConfiguration, CabinConfiguration, SeatCounts

load_dotenv()

PE_SVG_ID = "test-list-pe-aircraft"
NO_PE_SVG_ID = "test-list-no-pe-aircraft"
LONG_HAUL_AIRBUS_SVG_ID = "test-list-long-airbus"
SHORT_HAUL_BOEING_SVG_ID = "test-list-short-boeing"


@pytest.fixture(scope="module")
def client():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    init_schema()
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


@pytest.fixture
def seeded_configs(client):
    db = SessionLocal()
    try:
        with_pe = AircraftConfiguration(
            svg_id=PE_SVG_ID,
            airline_iata="PE",
            airline_name="Premium Air",
            aircraft_type_displayed="Widebody",
            aircraft_code_displayed="PE1",
            total_seats=324,
            configuration="6F 38J 24W 256M",
            seat_counts=SeatCounts(
                first=6,
                business=38,
                premium_economy=24,
                economy=256,
                total=324,
            ),
            cabins={
                "premium_economy": CabinConfiguration(
                    cabin_type="W",
                    cabin_class="Premium Economy",
                    num_seats=24,
                    pitch_inch=40,
                ),
            },
        )
        without_pe = AircraftConfiguration(
            svg_id=NO_PE_SVG_ID,
            airline_iata="NP",
            airline_name="No Premium Air",
            aircraft_type_displayed="Narrowbody",
            aircraft_code_displayed="NP1",
            total_seats=100,
            configuration="10J 90M",
            seat_counts=SeatCounts(business=10, economy=90, total=100),
            cabins={
                "business": CabinConfiguration(
                    cabin_type="J",
                    cabin_class="Business",
                    num_seats=10,
                ),
            },
        )
        upsert_aircraft(db, "pe", with_pe)
        upsert_aircraft(db, "np", without_pe)
        db.commit()
        yield PE_SVG_ID, NO_PE_SVG_ID
    finally:
        from backend.app.models.entities import AircraftConfiguration as AircraftEntity

        for svg_id in (PE_SVG_ID, NO_PE_SVG_ID):
            ac = db.query(AircraftEntity).filter(AircraftEntity.svg_id == svg_id).first()
            if ac:
                db.delete(ac)
        db.commit()
        db.close()


@pytest.fixture
def seeded_haul_manufacturer_configs(client):
    db = SessionLocal()
    try:
        long_haul_airbus = AircraftConfiguration(
            svg_id=LONG_HAUL_AIRBUS_SVG_ID,
            airline_iata="LH",
            airline_name="Long Haul Air",
            aircraft_type_displayed="Widebody",
            aircraft_code_displayed="LH1",
            manufacturer="Airbus",
            haul_type="Long Haul",
            total_seats=200,
            configuration="20J 180M",
            seat_counts=SeatCounts(business=20, economy=180, total=200),
            cabins={
                "business": CabinConfiguration(
                    cabin_type="J",
                    cabin_class="Business",
                    num_seats=20,
                ),
            },
        )
        short_haul_boeing = AircraftConfiguration(
            svg_id=SHORT_HAUL_BOEING_SVG_ID,
            airline_iata="SH",
            airline_name="Short Haul Air",
            aircraft_type_displayed="Narrowbody",
            aircraft_code_displayed="SH1",
            manufacturer="Boeing",
            haul_type="Short Haul",
            total_seats=150,
            configuration="12J 138M",
            seat_counts=SeatCounts(business=12, economy=138, total=150),
            cabins={
                "business": CabinConfiguration(
                    cabin_type="J",
                    cabin_class="Business",
                    num_seats=12,
                ),
            },
        )
        upsert_aircraft(db, "lh", long_haul_airbus)
        upsert_aircraft(db, "sh", short_haul_boeing)
        db.commit()
        yield LONG_HAUL_AIRBUS_SVG_ID, SHORT_HAUL_BOEING_SVG_ID
    finally:
        from backend.app.models.entities import AircraftConfiguration as AircraftEntity

        for svg_id in (LONG_HAUL_AIRBUS_SVG_ID, SHORT_HAUL_BOEING_SVG_ID):
            ac = db.query(AircraftEntity).filter(AircraftEntity.svg_id == svg_id).first()
            if ac:
                db.delete(ac)
        db.commit()
        db.close()


def _svg_ids(response_json: dict) -> list[str]:
    return [item["svg_id"] for item in response_json["items"]]


def test_list_aircraft_without_premium_economy_filter(client, seeded_configs) -> None:
    pe_svg_id, no_pe_svg_id = seeded_configs
    response = client.get("/api/v1/aircraft")
    assert response.status_code == 200
    svg_ids = _svg_ids(response.json())
    assert pe_svg_id in svg_ids
    assert no_pe_svg_id in svg_ids


def test_list_aircraft_with_premium_economy_filter(client, seeded_configs) -> None:
    pe_svg_id, no_pe_svg_id = seeded_configs
    response = client.get("/api/v1/aircraft?has_premium_economy=true")
    assert response.status_code == 200
    data = response.json()
    svg_ids = _svg_ids(data)
    assert pe_svg_id in svg_ids
    assert no_pe_svg_id not in svg_ids
    assert all(
        item.get("seat_counts", {}).get("premium_economy", 0) > 0
        for item in data["items"]
        if item["svg_id"] == pe_svg_id
    )


def test_list_aircraft_with_haul_type_filter(client, seeded_haul_manufacturer_configs) -> None:
    long_haul_id, short_haul_id = seeded_haul_manufacturer_configs
    response = client.get("/api/v1/aircraft?haul_type=Long%20Haul")
    assert response.status_code == 200
    svg_ids = _svg_ids(response.json())
    assert long_haul_id in svg_ids
    assert short_haul_id not in svg_ids


def test_list_aircraft_with_manufacturer_filter(client, seeded_haul_manufacturer_configs) -> None:
    long_haul_id, short_haul_id = seeded_haul_manufacturer_configs
    response = client.get("/api/v1/aircraft?manufacturer=Airbus")
    assert response.status_code == 200
    svg_ids = _svg_ids(response.json())
    assert long_haul_id in svg_ids
    assert short_haul_id not in svg_ids


def test_aircraft_filter_options(client, seeded_haul_manufacturer_configs) -> None:
    response = client.get("/api/v1/aircraft/filter-options")
    assert response.status_code == 200
    data = response.json()
    assert data["haul_types"] == ["Long Haul", "Short Haul"]
    assert "Airbus" in data["manufacturers"]
    assert "Boeing" in data["manufacturers"]
    assert data["manufacturers"] == sorted(data["manufacturers"], key=str.casefold)
