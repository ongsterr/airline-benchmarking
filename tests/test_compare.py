"""Tests for compare API endpoint."""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend.app.db.session import engine, init_schema
from backend.app.main import app
from backend.app.models.entities import Base
from shared.constants import MAX_COMPARE_CONFIGS

load_dotenv()


@pytest.fixture(scope="module")
def client():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    init_schema()
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_compare_rejects_more_than_max_ids(client: TestClient) -> None:
    ids = ",".join(f"id-{i}" for i in range(MAX_COMPARE_CONFIGS + 1))
    response = client.get(f"/api/v1/compare?ids={ids}")
    assert response.status_code == 400
    assert str(MAX_COMPARE_CONFIGS) in response.json()["detail"]


def test_compare_rejects_single_id(client: TestClient) -> None:
    response = client.get("/api/v1/compare?ids=only-one")
    assert response.status_code == 400
    assert "at least 2" in response.json()["detail"].lower()
