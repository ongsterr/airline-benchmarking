"""Tests for pipeline trigger API."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.db.migrate import ensure_pipeline_run_columns
from backend.app.db.session import SessionLocal, engine, init_schema
from backend.app.main import app
from backend.app.models.entities import Base, PipelineRun

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
    ensure_pipeline_run_columns()
    return TestClient(app)


def _clear_active_runs() -> None:
    db = SessionLocal()
    try:
        for run in db.query(PipelineRun).filter(PipelineRun.finished_at.is_(None)).all():
            run.finished_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _no_active_runs():
    _clear_active_runs()
    yield
    _clear_active_runs()


def test_trigger_hardware_requires_auth_when_enabled(client: TestClient, auth_enabled) -> None:
    response = client.post(
        "/api/v1/pipeline/hardware",
        json={"airlines": ["ek"]},
    )
    assert response.status_code == 401


def _sync_thread_class(monkeypatch) -> None:
    class SyncThread:
        def __init__(self, target, args=(), daemon=True):
            self._target = target
            self._args = args

        def start(self) -> None:
            self._target(*self._args)

    monkeypatch.setattr("backend.app.routers.pipeline.threading.Thread", SyncThread)


def test_trigger_hardware_dev_bypass(client: TestClient, monkeypatch) -> None:
    def fake_execute(db, run_record, airlines, force=False, limit=0, skip_existing=False):
        run_record.configs_discovered = 1
        run_record.configs_updated = 1
        run_record.finished_at = datetime.now(timezone.utc)

    monkeypatch.setattr("backend.app.routers.pipeline.execute_hardware_pipeline", fake_execute)
    _sync_thread_class(monkeypatch)

    response = client.post(
        "/api/v1/pipeline/hardware",
        json={"airlines": ["ek"], "skip_existing": True},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["pipeline_type"] == "hardware"
    assert data["status"] == "running"
    assert data["airlines"] == ["ek"]


def test_trigger_flight_with_auth(client: TestClient, auth_enabled, monkeypatch) -> None:
    def fake_execute(db, run_record, airlines, force=False, skip_existing=False):
        run_record.configs_discovered = 1
        run_record.configs_updated = 1
        run_record.finished_at = datetime.now(timezone.utc)

    monkeypatch.setattr("backend.app.routers.pipeline.execute_flight_pipeline", fake_execute)
    _sync_thread_class(monkeypatch)

    token = _login(client)
    response = client.post(
        "/api/v1/pipeline/flight",
        json={"airlines": ["ba"]},
        headers=_auth_headers(token),
    )
    assert response.status_code == 202
    assert response.json()["pipeline_type"] == "flight"


def test_trigger_rejects_when_run_in_progress(client: TestClient, auth_enabled) -> None:
    db = SessionLocal()
    active = PipelineRun(
        started_at=datetime.now(timezone.utc),
        airlines=["ek"],
        pipeline_type="hardware",
    )
    db.add(active)
    db.commit()
    db.close()

    token = _login(client)
    response = client.post(
        "/api/v1/pipeline/hardware",
        json={"airlines": ["ek"]},
        headers=_auth_headers(token),
    )
    assert response.status_code == 409


def test_get_pipeline_run(client: TestClient, auth_enabled, monkeypatch) -> None:
    finished_at = datetime.now(timezone.utc)

    def fake_execute(db, run_record, airlines, force=False, limit=0, skip_existing=False):
        run_record.configs_discovered = 2
        run_record.configs_updated = 1
        run_record.configs_skipped = 1
        run_record.finished_at = finished_at

    monkeypatch.setattr("backend.app.routers.pipeline.execute_hardware_pipeline", fake_execute)
    _sync_thread_class(monkeypatch)

    token = _login(client)
    trigger = client.post(
        "/api/v1/pipeline/hardware",
        json={"airlines": ["ek"]},
        headers=_auth_headers(token),
    )
    run_id = trigger.json()["id"]

    response = client.get(
        f"/api/v1/pipeline/runs/{run_id}",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["configs_updated"] == 1
    assert data["configs_skipped"] == 1


def test_get_active_pipeline_run(client: TestClient, auth_enabled) -> None:
    db = SessionLocal()
    active = PipelineRun(
        started_at=datetime.now(timezone.utc),
        airlines=["ek"],
        pipeline_type="flight",
    )
    db.add(active)
    db.commit()
    run_id = str(active.id)
    db.close()

    token = _login(client)
    response = client.get(
        "/api/v1/pipeline/runs/active",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert data["id"] == run_id
    assert data["status"] == "running"


def test_trigger_requires_at_least_one_airline(client: TestClient, auth_enabled) -> None:
    token = _login(client)
    response = client.post(
        "/api/v1/pipeline/hardware",
        json={"airlines": []},
        headers=_auth_headers(token),
    )
    assert response.status_code == 400


def test_get_pipeline_run_invalid_id(client: TestClient, auth_enabled) -> None:
    token = _login(client)
    response = client.get(
        "/api/v1/pipeline/runs/not-a-uuid",
        headers=_auth_headers(token),
    )
    assert response.status_code == 400


def test_get_pipeline_run_not_found(client: TestClient, auth_enabled) -> None:
    token = _login(client)
    response = client.get(
        f"/api/v1/pipeline/runs/{uuid.uuid4()}",
        headers=_auth_headers(token),
    )
    assert response.status_code == 404
