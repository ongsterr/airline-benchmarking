"""Tests for airline upsert name preservation."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from dotenv import load_dotenv

from backend.app.db.session import SessionLocal, engine, init_schema
from backend.app.models.entities import Airline, Base
from pipeline.load import (
    _is_code_like_name,
    _should_update_airline_name,
    get_or_create_airline,
)

load_dotenv()


def test_is_code_like_name_matches_slug_or_iata() -> None:
    assert _is_code_like_name("CX", "cx", "CX") is True
    assert _is_code_like_name("cx", "cx", None) is True
    assert _is_code_like_name("Cathay Pacific", "cx", "CX") is False


def test_should_update_skips_code_like_over_display_name() -> None:
    airline = SimpleNamespace(name="Cathay Pacific")
    assert _should_update_airline_name(airline, "cx", "CX", "CX") is False
    assert _should_update_airline_name(airline, "cx", "British Airways", "BA") is True


def test_should_update_allows_code_like_when_existing_is_code_like() -> None:
    airline = SimpleNamespace(name="BA")
    assert _should_update_airline_name(airline, "ba", "British Airways", "BA") is True


@pytest.fixture
def db():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    init_schema()
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    for slug in ("tuups1", "tuups2", "tuups3"):
        row = session.query(Airline).filter(Airline.slug == slug).first()
        if row:
            session.delete(row)
    session.commit()
    session.close()


def test_preserves_display_name_when_flight_pipeline_passes_code(db) -> None:
    airline = get_or_create_airline(db, "tuups1", "Cathay Pacific", "CX")
    db.commit()
    assert airline.name == "Cathay Pacific"

    updated = get_or_create_airline(db, "tuups1", "CX", "CX")
    db.commit()
    assert updated.name == "Cathay Pacific"


def test_updates_code_like_name_to_display_name(db) -> None:
    airline = get_or_create_airline(db, "tuups2", "BA", "BA")
    db.commit()
    assert airline.name == "BA"

    updated = get_or_create_airline(db, "tuups2", "British Airways", "BA")
    db.commit()
    assert updated.name == "British Airways"


def test_new_airline_gets_code_like_fallback_name(db) -> None:
    airline = get_or_create_airline(db, "tuups3", "NZ", "NZ")
    db.commit()
    assert airline.name == "NZ"
