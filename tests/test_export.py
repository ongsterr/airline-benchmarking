"""Tests for fleet CSV export endpoint."""

from __future__ import annotations

import csv
import os
from io import StringIO

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal, init_schema
from backend.app.main import app
from backend.app.models.entities import Base
from backend.app.db.session import engine
from pipeline.load import upsert_aircraft
from shared.compare_fields import AIRCRAFT_FIELDS, CABIN_FIELDS
from shared.schemas import AircraftConfiguration, CabinConfiguration, SeatCounts

load_dotenv()

TEST_SVG_ID = "test-export-aircraft"
SECOND_SVG_ID = "atest-export-aircraft"


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
        first = AircraftConfiguration(
            svg_id=TEST_SVG_ID,
            airline_iata="TS",
            airline_name='Test, "Air"',
            aircraft_type_displayed="Test Type",
            aircraft_code_displayed="TST",
            manufacturer='Maker, "Quoted"',
            total_seats=100,
            fleet_count=2,
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
                "economy": CabinConfiguration(
                    cabin_type="M",
                    cabin_class="Economy",
                    num_seats=90,
                    pitch_inch=31,
                    has_flat_bed=False,
                ),
            },
        )
        second = AircraftConfiguration(
            svg_id=SECOND_SVG_ID,
            airline_iata="AS",
            airline_name="Alpha Air",
            aircraft_type_displayed="Alpha Type",
            aircraft_code_displayed="ALP",
            manufacturer="Alpha Maker",
            total_seats=40,
            fleet_count=1,
            configuration="8J 32M",
            seat_counts=SeatCounts(business=8, economy=32, total=40),
            cabins={
                "business": CabinConfiguration(
                    cabin_type="J",
                    cabin_class="Business",
                    num_seats=8,
                    pitch_inch=44,
                    has_flat_bed=True,
                ),
            },
        )
        upsert_aircraft(db, "ts", first)
        upsert_aircraft(db, "as", second)
        db.commit()
        yield TEST_SVG_ID, SECOND_SVG_ID
    finally:
        from backend.app.models.entities import AircraftConfiguration as AircraftEntity

        for svg_id in (TEST_SVG_ID, SECOND_SVG_ID):
            ac = db.query(AircraftEntity).filter(AircraftEntity.svg_id == svg_id).first()
            if ac:
                db.delete(ac)
        db.commit()
        db.close()


def _read_export_rows(content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(content)))


def test_export_csv_for_selected_configs(client, seeded_config) -> None:
    first_svg_id, second_svg_id = seeded_config
    response = client.get(f"/api/v1/export.csv?ids={first_svg_id}")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment; filename=" in response.headers["content-disposition"]

    rows = _read_export_rows(response.text)
    assert len(rows) == 2
    assert rows[0].keys() == {
        "airline_name",
        "svg_id",
        "aircraft_type_displayed",
        "aircraft_code_displayed",
        "cabin_class",
        "cabin_key",
        *AIRCRAFT_FIELDS,
        *CABIN_FIELDS,
    }
    assert [row["cabin_key"] for row in rows] == ["business", "economy"]
    assert all(row["svg_id"] == first_svg_id for row in rows)
    assert rows[0]["manufacturer"] == 'Maker, "Quoted"'
    assert rows[0]["has_flat_bed"] == "true"
    assert rows[1]["has_flat_bed"] == "false"
    assert '"Test, ""Air"""' in response.text

    multi_response = client.get(f"/api/v1/export.csv?ids={first_svg_id},{second_svg_id}")
    multi_rows = _read_export_rows(multi_response.text)
    assert [row["svg_id"] for row in multi_rows] == [
        second_svg_id,
        first_svg_id,
        first_svg_id,
    ]


def test_export_csv_allows_more_than_four_ids(client) -> None:
    response = client.get("/api/v1/export.csv?ids=a,b,c,d,e")
    assert response.status_code == 200
    rows = _read_export_rows(response.text)
    assert rows == []
