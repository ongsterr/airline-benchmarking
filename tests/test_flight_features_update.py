"""Tests for airline cabin flight features PATCH API."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.db.session import SessionLocal, engine, init_schema
from backend.app.main import app
from backend.app.models.entities import Base
from pipeline.flight_load import upsert_flight_features
from shared.flight_fields import coerce_flight_field_value
from shared.schemas import AirlineFlightFeatures, CabinFlightFeatures

load_dotenv()

TEST_PASSWORD = "test-edit-password"
TEST_SESSION_SECRET = "test-session-secret-key-for-hmac"


@pytest.fixture(autouse=True)
def _reset_edit_auth(monkeypatch):
    monkeypatch.setattr(settings, "edit_password", "")
    monkeypatch.setattr(settings, "session_secret", "")


@pytest.fixture
def auth_enabled(monkeypatch):
    monkeypatch.setattr(settings, "edit_password", TEST_PASSWORD)
    monkeypatch.setattr(settings, "session_secret", TEST_SESSION_SECRET)


def _login(client: TestClient, password: str = TEST_PASSWORD) -> str:
    response = client.post("/api/v1/auth/login", json={"password": password})
    assert response.status_code == 200
    return response.json()["token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


def test_coerce_flight_field_value() -> None:
    assert coerce_flight_field_value("checked_bag_pieces", "3") == 3
    assert coerce_flight_field_value("check_in_priority", "") is None
    assert coerce_flight_field_value("amenity_kit", "socks, eye mask") == [
        "socks",
        "eye mask",
    ]
    assert coerce_flight_field_value("amenity_kit", "") is None


def test_coerce_rejects_unknown_flight_field() -> None:
    with pytest.raises(ValueError, match="Unknown flight field"):
        coerce_flight_field_value("not_a_field", "x")


def test_patch_requires_auth_when_enabled(
    auth_enabled, client: TestClient, seeded_flight_data
) -> None:
    response = client.patch(
        "/api/v1/airlines/ek/flight-features?cabin=business",
        json={"fields": {"check_in_priority": "No"}},
    )
    assert response.status_code == 401


def test_patch_check_in_priority(
    client: TestClient, seeded_flight_data
) -> None:
    response = client.patch(
        "/api/v1/airlines/ek/flight-features?cabin=business",
        json={"fields": {"check_in_priority": "No"}},
    )
    assert response.status_code == 200
    assert response.json()["check_in_priority"] == "No"

    compare = client.get("/api/v1/compare/airlines?slugs=ek,ba&cabin=business")
    assert compare.status_code == 200
    rows = compare.json()["rows"]
    check_in_row = next(r for r in rows if r["field_key"] == "check_in_priority")
    assert check_in_row["values"]["ek"] == "No"


def test_patch_source_url(client: TestClient, seeded_flight_data) -> None:
    response = client.patch(
        "/api/v1/airlines/ek/flight-features?cabin=business",
        json={"source_url": "https://example.com/ek-updated"},
    )
    assert response.status_code == 200

    compare = client.get("/api/v1/compare/airlines?slugs=ek,ba&cabin=business")
    assert compare.status_code == 200
    source_row = next(
        r for r in compare.json()["rows"] if r["field_key"] == "source_url"
    )
    assert source_row["values"]["ek"] == "https://example.com/ek-updated"


def test_patch_with_token_when_auth_enabled(
    auth_enabled, client: TestClient, seeded_flight_data
) -> None:
    token = _login(client)
    response = client.patch(
        "/api/v1/airlines/ek/flight-features?cabin=business",
        json={"fields": {"lounge_access": "No"}},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["lounge_access"] == "No"


def test_patch_rejects_unknown_field(
    client: TestClient, seeded_flight_data
) -> None:
    response = client.patch(
        "/api/v1/airlines/ek/flight-features?cabin=business",
        json={"fields": {"not_a_field": "x"}},
    )
    assert response.status_code == 422


def test_patch_rejects_empty_body(
    client: TestClient, seeded_flight_data
) -> None:
    response = client.patch(
        "/api/v1/airlines/ek/flight-features?cabin=business",
        json={},
    )
    assert response.status_code == 422
