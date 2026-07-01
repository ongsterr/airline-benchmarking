"""Tests for airline flight compare API."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal, engine, init_schema
from backend.app.main import app
from backend.app.models.entities import Base
from pipeline.flight_load import upsert_flight_features, upsert_flight_sources
from shared.constants import MAX_COMPARE_CONFIGS
from shared.schemas import AirlineFlightFeatures, CabinFlightFeatures, FlightSourceCandidate

load_dotenv()


@pytest.fixture(scope="module")
def client():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    init_schema()
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


@pytest.fixture(scope="module")
def seeded_flight_data(client: TestClient):
    db = SessionLocal()
    cabin = CabinFlightFeatures(
        cabin_class="Business",
        check_in_priority="Yes",
        checked_bag_pieces=2,
        lounge_access="Yes",
    )
    upsert_flight_features(
        db,
        "test-cmp-a",
        "Compare Test A",
        "A1",
        AirlineFlightFeatures(cabins={"business": cabin}),
        "https://example.com/test-cmp-a",
        datetime.now(timezone.utc),
    )
    upsert_flight_features(
        db,
        "test-cmp-b",
        "Compare Test B",
        "B1",
        AirlineFlightFeatures(
            cabins={
                "business": CabinFlightFeatures(
                    cabin_class="Business",
                    check_in_priority="Yes",
                    checked_bag_pieces=2,
                )
            }
        ),
        "https://example.com/test-cmp-b",
        datetime.now(timezone.utc),
    )
    db.commit()
    db.close()
    yield


def test_compare_airlines_rejects_single_slug(client: TestClient) -> None:
    response = client.get("/api/v1/compare/airlines?slugs=ek")
    assert response.status_code == 400


def test_compare_airlines_rejects_too_many(client: TestClient) -> None:
    slugs = ",".join(f"a{i}" for i in range(MAX_COMPARE_CONFIGS + 1))
    response = client.get(f"/api/v1/compare/airlines?slugs={slugs}")
    assert response.status_code == 400


def test_compare_airlines_returns_flight_rows(
    client: TestClient, seeded_flight_data
) -> None:
    response = client.get("/api/v1/compare/airlines?slugs=test-cmp-a,test-cmp-b&cabin=business")
    assert response.status_code == 200
    data = response.json()
    assert len(data["columns"]) == 2
    assert any(row["scope"] == "flight" for row in data["rows"])


def test_compare_airlines_includes_source_url_row(
    client: TestClient, seeded_flight_data
) -> None:
    response = client.get("/api/v1/compare/airlines?slugs=test-cmp-a,test-cmp-b&cabin=business")
    assert response.status_code == 200
    data = response.json()
    source_rows = [r for r in data["rows"] if r["field_key"] == "source_url"]
    assert len(source_rows) == 1
    row = source_rows[0]
    assert row["feature"] == "Reference URLs"
    assert len(row["values"]["test-cmp-a"]) == 1
    assert row["values"]["test-cmp-a"][0]["url"] == "https://example.com/test-cmp-a"
    assert len(row["values"]["test-cmp-b"]) == 1
    assert row["values"]["test-cmp-b"][0]["url"] == "https://example.com/test-cmp-b"


def test_compare_airlines_includes_all_flight_sources_for_cabin(
    client: TestClient, seeded_flight_data
) -> None:
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    upsert_flight_sources(
        db,
        "test-cmp-a",
        "Compare Test A",
        "A1",
        [
            (
                FlightSourceCandidate(
                    url="https://example.com/ek-business",
                    cabin_keys=["business"],
                    page_type="cabin_product",
                    title="Business cabin",
                ),
                200,
                now,
            ),
            (
                FlightSourceCandidate(
                    url="https://example.com/ek-baggage",
                    cabin_keys=["business"],
                    page_type="baggage",
                    title="Baggage",
                ),
                200,
                now,
            ),
            (
                FlightSourceCandidate(
                    url="https://example.com/ek-first-only",
                    cabin_keys=["first"],
                    page_type="cabin_product",
                    title="First cabin",
                ),
                200,
                now,
            ),
        ],
    )
    db.commit()
    db.close()

    response = client.get("/api/v1/compare/airlines?slugs=test-cmp-a,test-cmp-b&cabin=business")
    assert response.status_code == 200
    data = response.json()
    source_row = next(r for r in data["rows"] if r["field_key"] == "source_url")
    ek_urls = [source["url"] for source in source_row["values"]["test-cmp-a"]]
    assert ek_urls == [
        "https://example.com/ek-business",
        "https://example.com/ek-baggage",
    ]
    assert source_row["values"]["test-cmp-b"][0]["url"] == "https://example.com/test-cmp-b"
