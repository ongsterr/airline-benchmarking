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
from pipeline.flight_load import upsert_flight_features
from shared.constants import MAX_COMPARE_CONFIGS
from shared.schemas import AirlineFlightFeatures, CabinFlightFeatures

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
        "ek",
        "Emirates",
        "EK",
        AirlineFlightFeatures(cabins={"business": cabin}),
        "https://example.com/ek",
        datetime.now(timezone.utc),
    )
    upsert_flight_features(
        db,
        "ba",
        "British Airways",
        "BA",
        AirlineFlightFeatures(
            cabins={
                "business": CabinFlightFeatures(
                    cabin_class="Business",
                    check_in_priority="Yes",
                    checked_bag_pieces=2,
                )
            }
        ),
        "https://example.com/ba",
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
    response = client.get("/api/v1/compare/airlines?slugs=ek,ba&cabin=business")
    assert response.status_code == 200
    data = response.json()
    assert len(data["columns"]) == 2
    assert any(row["scope"] == "flight" for row in data["rows"])
