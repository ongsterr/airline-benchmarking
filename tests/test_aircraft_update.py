"""Tests for compare field coercion and aircraft config PATCH."""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal, init_schema
from backend.app.main import app
from backend.app.models.entities import Base
from backend.app.db.session import engine
from pipeline.load import upsert_aircraft
from shared.compare_fields import coerce_field_value, format_compare_value
from shared.schemas import (
    AircraftConfiguration,
    CabinConfiguration,
    SeatCounts,
)

load_dotenv()

TEST_SVG_ID = "test-patch-aircraft"


@pytest.fixture(scope="module")
def client():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    init_schema()
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


@pytest.fixture
def seeded_config(client):
    db = SessionLocal()
    try:
        data = AircraftConfiguration(
            svg_id=TEST_SVG_ID,
            airline_iata="TS",
            airline_name="Test Air",
            aircraft_type_displayed="Test Type",
            aircraft_code_displayed="TST",
            manufacturer="TestCo",
            total_seats=100,
            fleet_count=1,
            configuration="10J 90M",
            seat_counts=SeatCounts(business=10, economy=90, total=100),
            cabins={
                "business": CabinConfiguration(
                    cabin_type="J",
                    cabin_class="Business",
                    num_seats=10,
                    pitch_inch=42,
                    has_flat_bed=True,
                ),
            },
        )
        upsert_aircraft(db, "ts", data)
        db.commit()
        yield TEST_SVG_ID
    finally:
        from backend.app.models.entities import AircraftConfiguration as AircraftEntity

        ac = db.query(AircraftEntity).filter(AircraftEntity.svg_id == TEST_SVG_ID).first()
        if ac:
            db.delete(ac)
            db.commit()
        db.close()


def test_format_compare_value() -> None:
    assert format_compare_value(None) == "—"
    assert format_compare_value(True) == "Yes"
    assert format_compare_value(False) == "No"
    assert format_compare_value(42) == 42


def test_coerce_field_value_types() -> None:
    assert coerce_field_value("total_seats", "200") == 200
    assert coerce_field_value("pitch_inch", "78.5") == 78.5
    assert coerce_field_value("has_flat_bed", "yes") is True
    assert coerce_field_value("manufacturer", "") is None


def test_coerce_rejects_unknown_field() -> None:
    with pytest.raises(ValueError, match="Unknown field"):
        coerce_field_value("not_a_field", "x")


def test_patch_multiple_aircraft_fields(client, seeded_config) -> None:
    response = client.patch(
        f"/api/v1/aircraft/{seeded_config}",
        json={
            "aircraft": {
                "total_seats": 210,
                "manufacturer": "Airbus",
            }
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_seats"] == 210
    assert body["manufacturer"] == "Airbus"


def test_patch_multiple_cabin_fields(client, seeded_config) -> None:
    response = client.patch(
        f"/api/v1/aircraft/{seeded_config}",
        json={
            "cabins": {
                "business": {
                    "pitch_inch": 78,
                    "width_inch": 21,
                    "has_flat_bed": True,
                }
            }
        },
    )
    assert response.status_code == 200
    cabin = response.json()["cabins"]["business"]
    assert cabin["pitch_inch"] == 78
    assert cabin["width_inch"] == 21
    assert cabin["has_flat_bed"] is True


def test_patch_aircraft_and_cabin_together(client, seeded_config) -> None:
    response = client.patch(
        f"/api/v1/aircraft/{seeded_config}",
        json={
            "aircraft": {"fleet_count": 5},
            "cabins": {"business": {"num_seats": 12}},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fleet_count"] == 5
    assert body["cabins"]["business"]["num_seats"] == 12


def test_patch_rejects_unknown_field(client, seeded_config) -> None:
    response = client.patch(
        f"/api/v1/aircraft/{seeded_config}",
        json={"aircraft": {"not_a_field": "x"}},
    )
    assert response.status_code == 422


def test_patch_rejects_empty_body(client, seeded_config) -> None:
    response = client.patch(f"/api/v1/aircraft/{seeded_config}", json={})
    assert response.status_code == 422


def test_patch_404_unknown_svg(client) -> None:
    response = client.patch(
        "/api/v1/aircraft/does-not-exist-xyz",
        json={"aircraft": {"total_seats": 1}},
    )
    assert response.status_code == 404
