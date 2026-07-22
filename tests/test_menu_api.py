"""Tests for menu filter-options and compare API endpoints."""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal, engine, init_schema
from backend.app.main import app
from backend.app.models.entities import Base, MenuCapture, MenuItem, MenuObservation
from pipeline.load import get_or_create_airline
from shared.constants import MAX_COMPARE_CONFIGS

load_dotenv()


@pytest.fixture(scope="module")
def client():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    init_schema()
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def _add_item(
    db,
    observation: MenuObservation,
    *,
    category: str,
    subcategory: str,
    code: str,
    title: str,
    position: int,
    item_type: str | None = None,
    beverage_type: str | None = None,
    is_vegetarian: bool | None = None,
    is_vegan: bool | None = None,
    is_localized: bool | None = None,
    enriched: bool = True,
) -> MenuItem:
    now = datetime.now(timezone.utc) if enriched else None
    item = MenuItem(
        id=uuid4(),
        observation_id=observation.id,
        category=category,
        subcategory=subcategory,
        code=code,
        title=title,
        desc=f"Desc for {title}",
        position=position,
        item_hash=f"m:{code}",
        item_type=item_type,
        beverage_type=beverage_type,
        is_vegetarian=is_vegetarian,
        is_vegan=is_vegan,
        is_localized=is_localized,
        localization_confidence=0.9 if is_localized is not None else None,
        localization_note="note" if is_localized else None,
        enrichment_version="menu_enrichment_v1" if enriched else None,
        enriched_at=now,
    )
    db.add(item)
    return item


def _seed_observation(
    db,
    *,
    airline,
    flight_number: str,
    origin: str,
    dest: str,
    service_date: date,
    cabin_code: str,
    cabin_norm: str,
    confidence_tier: int = 1,
    source_url: str = (
        "https://www.emirates.com/ae/english/experience/dining/onboard-menu/"
        "?date=2026-08-01&flight=582&origin=DXB&destination=DAC&cabinclass=j&view=1"
    ),
) -> MenuObservation:
    capture = MenuCapture(
        id=uuid4(),
        source_id="emirates-onboard-menu",
        airline_id=airline.id,
        source_url=source_url,
        cabin_code=cabin_code,
        flight_number=flight_number,
        origin_iata=origin,
        dest_iata=dest,
        service_date=service_date,
        captured_at=datetime.now(timezone.utc),
        media_type="application/json",
        http_status=200,
        default_tier=1,
    )
    db.add(capture)
    db.flush()
    observation = MenuObservation(
        id=uuid4(),
        capture_id=capture.id,
        airline_id=airline.id,
        cabin_norm=cabin_norm,
        cabin_marketing=cabin_norm.replace("_", " ").title(),
        origin_iata=origin,
        dest_iata=dest,
        direction="outbound",
        menu_cycle=service_date.strftime("%Y-%m"),
        service_date=service_date,
        grain_observed=["airline", "cabin", "route", "direction", "date"],
        confidence_tier=confidence_tier,
        extractor_version="menu_api_transform_v2",
        extracted_at=datetime.now(timezone.utc),
    )
    db.add(observation)
    db.flush()
    return observation


@pytest.fixture
def seeded_menu(client: TestClient):
    db = SessionLocal()
    airline = get_or_create_airline(db, "tst-mapi", "Menu API Test", "TM")
    service = date(2026, 8, 1)
    # Unique flight numbers per run to avoid capture unique-key collisions
    suffix = uuid4().hex[:4]
    flight_a = f"5{suffix}"[:5]
    flight_b = f"7{suffix}"[:5]
    flight_empty = f"9{suffix}"[:5]

    obs_a = _seed_observation(
        db,
        airline=airline,
        flight_number=flight_a,
        origin="DXB",
        dest="DAC",
        service_date=service,
        cabin_code="j",
        cabin_norm="business",
    )
    _add_item(
        db,
        obs_a,
        category="Breakfast",
        subcategory="Main Course",
        code="F1",
        title="Vegan Bowl",
        position=1,
        item_type="food",
        is_vegetarian=True,
        is_vegan=True,
        is_localized=True,
    )
    _add_item(
        db,
        obs_a,
        category="Breakfast",
        subcategory="Main Course",
        code="F2",
        title="Chicken Plate",
        position=2,
        item_type="food",
        is_vegetarian=False,
        is_vegan=False,
        is_localized=False,
    )
    _add_item(
        db,
        obs_a,
        category="Beverages",
        subcategory="Wine",
        code="B1",
        title="Red Wine",
        position=3,
        item_type="beverage",
        beverage_type="alcoholic",
    )
    _add_item(
        db,
        obs_a,
        category="Beverages",
        subcategory="Soft Drinks",
        code="B2",
        title="Orange Juice",
        position=4,
        item_type="beverage",
        beverage_type="non_alcoholic",
    )
    _add_item(
        db,
        obs_a,
        category="Breakfast",
        subcategory="Dessert",
        code="F3",
        title="Mystery Dessert",
        position=5,
        item_type=None,
        enriched=False,
    )

    obs_b = _seed_observation(
        db,
        airline=airline,
        flight_number=flight_b,
        origin="DXB",
        dest="LHR",
        service_date=service,
        cabin_code="j",
        cabin_norm="business",
    )
    _add_item(
        db,
        obs_b,
        category="Breakfast",
        subcategory="Main Course",
        code="F10",
        title="Veg Omelette",
        position=1,
        item_type="food",
        is_vegetarian=True,
        is_vegan=False,
        is_localized=False,
    )
    _add_item(
        db,
        obs_b,
        category="Beverages",
        subcategory="Soft Drinks",
        code="B10",
        title="Sparkling Water",
        position=2,
        item_type="beverage",
        beverage_type="non_alcoholic",
    )

    obs_empty = _seed_observation(
        db,
        airline=airline,
        flight_number=flight_empty,
        origin="DXB",
        dest="JFK",
        service_date=service,
        cabin_code="j",
        cabin_norm="business",
        confidence_tier=3,
    )

    obs_economy = _seed_observation(
        db,
        airline=airline,
        flight_number=flight_a,
        origin="DXB",
        dest="DAC",
        service_date=service,
        cabin_code="y",
        cabin_norm="economy",
    )
    _add_item(
        db,
        obs_economy,
        category="Breakfast",
        subcategory="Main Course",
        code="YE1",
        title="Economy Meal",
        position=1,
        item_type="food",
        is_vegetarian=False,
        is_vegan=False,
        is_localized=False,
    )

    db.commit()
    payload = {
        "obs_a": str(obs_a.id),
        "obs_b": str(obs_b.id),
        "obs_empty": str(obs_empty.id),
        "obs_economy": str(obs_economy.id),
    }
    db.close()
    yield payload


def test_filter_options_rejects_invalid_cabin(client: TestClient) -> None:
    response = client.get("/api/v1/menu/filter-options?cabin=suite")
    assert response.status_code == 400


def test_filter_options_rejects_invalid_item_type(client: TestClient) -> None:
    response = client.get("/api/v1/menu/filter-options?cabin=business&item_type=snack")
    assert response.status_code == 400


def test_filter_options_hides_test_airline_captures(
    client: TestClient, seeded_menu
) -> None:
    response = client.get("/api/v1/menu/filter-options?cabin=business&item_type=all")
    assert response.status_code == 200
    ids = {o["observation_id"] for o in response.json()["observations"]}
    # tst-mapi fixture rows must not appear in the UI dropdown
    assert seeded_menu["obs_a"] not in ids
    assert seeded_menu["obs_b"] not in ids
    assert seeded_menu["obs_empty"] not in ids
    assert seeded_menu["obs_economy"] not in ids


def test_filter_options_returns_displayable_observations(client: TestClient) -> None:
    db = SessionLocal()
    airline = get_or_create_airline(db, "dmmenu", "Display Menu Airline", "DM")
    suffix = uuid4().hex[:4]
    obs_biz = _seed_observation(
        db,
        airline=airline,
        flight_number=f"1{suffix}"[:5],
        origin="DXB",
        dest="DAC",
        service_date=date(2026, 8, 1),
        cabin_code="j",
        cabin_norm="business",
    )
    _add_item(
        db,
        obs_biz,
        category="Breakfast",
        subcategory="Main Course",
        code="DM1",
        title="Display Meal",
        position=1,
        item_type="food",
        is_vegetarian=True,
        is_vegan=False,
        is_localized=False,
    )
    _add_item(
        db,
        obs_biz,
        category="Beverages",
        subcategory="Wine",
        code="DM2",
        title="Display Wine",
        position=2,
        item_type="beverage",
        beverage_type="alcoholic",
    )
    obs_empty = _seed_observation(
        db,
        airline=airline,
        flight_number=f"2{suffix}"[:5],
        origin="DXB",
        dest="LHR",
        service_date=date(2026, 8, 1),
        cabin_code="j",
        cabin_norm="business",
        confidence_tier=3,
    )
    obs_economy = _seed_observation(
        db,
        airline=airline,
        flight_number=f"1{suffix}"[:5],
        origin="DXB",
        dest="DAC",
        service_date=date(2026, 8, 1),
        cabin_code="y",
        cabin_norm="economy",
    )
    _add_item(
        db,
        obs_economy,
        category="Breakfast",
        subcategory="Main Course",
        code="DME1",
        title="Economy Display Meal",
        position=1,
        item_type="food",
        is_vegetarian=False,
        is_vegan=False,
        is_localized=False,
    )
    biz_id = str(obs_biz.id)
    empty_id = str(obs_empty.id)
    economy_id = str(obs_economy.id)
    capture_ids = [obs_biz.capture_id, obs_empty.capture_id, obs_economy.capture_id]
    db.commit()

    try:
        response = client.get("/api/v1/menu/filter-options?cabin=business&item_type=all")
        assert response.status_code == 200
        data = response.json()
        ids = {o["observation_id"] for o in data["observations"]}
        assert biz_id in ids
        assert empty_id in ids
        assert economy_id not in ids
        empty = next(o for o in data["observations"] if o["observation_id"] == empty_id)
        assert empty["available"] is False

        food = client.get("/api/v1/menu/filter-options?cabin=business&item_type=food")
        assert food.status_code == 200
        by_id = {o["observation_id"]: o for o in food.json()["observations"]}
        assert by_id[biz_id]["item_count"] == 1
    finally:
        for oid in (obs_biz.id, obs_empty.id, obs_economy.id):
            db.query(MenuItem).filter(MenuItem.observation_id == oid).delete()
            db.query(MenuObservation).filter(MenuObservation.id == oid).delete()
        for cid in capture_ids:
            db.query(MenuCapture).filter(MenuCapture.id == cid).delete()
        db.commit()
        db.close()


def test_filter_options_hides_example_com_menu_captures(client: TestClient) -> None:
    db = SessionLocal()
    # Displayable airline slug, but fixture source_url must still be hidden
    airline = get_or_create_airline(db, "dmhide", "Menu Hide Source", "DH")
    suffix = uuid4().hex[:4]
    obs = _seed_observation(
        db,
        airline=airline,
        flight_number=f"8{suffix}"[:5],
        origin="DXB",
        dest="BOM",
        service_date=date(2026, 8, 1),
        cabin_code="j",
        cabin_norm="business",
        source_url="https://example.com/menu",
    )
    _add_item(
        db,
        obs,
        category="Breakfast",
        subcategory="Main Course",
        code="HIDE1",
        title="Hidden Fixture Meal",
        position=1,
        item_type="food",
        is_vegetarian=True,
        is_vegan=False,
        is_localized=False,
    )
    obs_id = str(obs.id)
    capture_id = obs.capture_id
    db.commit()

    try:
        response = client.get("/api/v1/menu/filter-options?cabin=business&item_type=all")
        assert response.status_code == 200
        ids = {o["observation_id"] for o in response.json()["observations"]}
        assert obs_id not in ids
    finally:
        db.query(MenuItem).filter(MenuItem.observation_id == obs.id).delete()
        db.query(MenuObservation).filter(MenuObservation.id == obs.id).delete()
        db.query(MenuCapture).filter(MenuCapture.id == capture_id).delete()
        db.commit()
        db.close()


def test_compare_rejects_single_id(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/menu/compare?observation_ids={uuid4()}&cabin=business"
    )
    assert response.status_code == 400
    assert "at least 2" in response.json()["detail"].lower()


def test_compare_rejects_too_many(client: TestClient) -> None:
    ids = ",".join(str(uuid4()) for _ in range(MAX_COMPARE_CONFIGS + 1))
    response = client.get(f"/api/v1/menu/compare?observation_ids={ids}&cabin=business")
    assert response.status_code == 400
    assert str(MAX_COMPARE_CONFIGS) in response.json()["detail"]


def test_compare_rejects_invalid_uuid(client: TestClient) -> None:
    response = client.get(
        "/api/v1/menu/compare?observation_ids=not-a-uuid,also-bad&cabin=business"
    )
    assert response.status_code == 400


def test_compare_rejects_cabin_mismatch(client: TestClient, seeded_menu) -> None:
    ids = f"{seeded_menu['obs_a']},{seeded_menu['obs_economy']}"
    response = client.get(f"/api/v1/menu/compare?observation_ids={ids}&cabin=business")
    assert response.status_code == 400
    assert "cabin" in response.json()["detail"].lower()


def test_compare_summary_and_detail(client: TestClient, seeded_menu) -> None:
    ids = f"{seeded_menu['obs_a']},{seeded_menu['obs_b']}"
    response = client.get(
        f"/api/v1/menu/compare?observation_ids={ids}&cabin=business&item_type=all"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["columns"]) == 2
    assert data["columns"][0]["observation_id"] == seeded_menu["obs_a"]
    assert data["columns"][1]["observation_id"] == seeded_menu["obs_b"]

    summary_keys = {(r["category"], r["subcategory"]) for r in data["summary_rows"]}
    assert ("Breakfast", "Main Course") in summary_keys
    assert ("Beverages", "Wine") in summary_keys
    assert ("Beverages", "Soft Drinks") in summary_keys
    assert ("Breakfast", "Dessert") in summary_keys

    main = next(
        r
        for r in data["summary_rows"]
        if r["category"] == "Breakfast" and r["subcategory"] == "Main Course"
    )
    counts_a = main["values"][seeded_menu["obs_a"]]
    assert counts_a["vegetarian"] == 1
    assert counts_a["vegan"] == 1
    assert counts_a["localized"] == 1
    assert counts_a["alcoholic"] == 0
    assert counts_a["total_items"] == 2

    wine = next(
        r
        for r in data["summary_rows"]
        if r["category"] == "Beverages" and r["subcategory"] == "Wine"
    )
    wine_a = wine["values"][seeded_menu["obs_a"]]
    assert wine_a["alcoholic"] == 1
    assert wine_a["non_alcoholic"] == 0
    # Flight B has no Wine subcategory entries → zeros
    wine_b = wine["values"][seeded_menu["obs_b"]]
    assert wine_b["total_items"] == 0

    dessert = next(
        r
        for r in data["summary_rows"]
        if r["category"] == "Breakfast" and r["subcategory"] == "Dessert"
    )
    dessert_a = dessert["values"][seeded_menu["obs_a"]]
    assert dessert_a["total_items"] == 1
    assert dessert_a["enriched_items"] == 0
    assert dessert_a["vegetarian"] == 0  # null not counted

    detail_main = next(
        r
        for r in data["detail_rows"]
        if r["category"] == "Breakfast" and r["subcategory"] == "Main Course"
    )
    titles_a = [i["title"] for i in detail_main["values"][seeded_menu["obs_a"]]]
    assert titles_a == ["Vegan Bowl", "Chicken Plate"]
    titles_b = [i["title"] for i in detail_main["values"][seeded_menu["obs_b"]]]
    assert titles_b == ["Veg Omelette"]


def test_compare_food_filter(client: TestClient, seeded_menu) -> None:
    ids = f"{seeded_menu['obs_a']},{seeded_menu['obs_b']}"
    response = client.get(
        f"/api/v1/menu/compare?observation_ids={ids}&cabin=business&item_type=food"
    )
    assert response.status_code == 200
    data = response.json()
    cats = {r["category"] for r in data["summary_rows"]}
    assert "Beverages" not in cats
    assert "Breakfast" in cats


def test_compare_empty_observation(client: TestClient, seeded_menu) -> None:
    ids = f"{seeded_menu['obs_a']},{seeded_menu['obs_empty']}"
    response = client.get(
        f"/api/v1/menu/compare?observation_ids={ids}&cabin=business&item_type=all"
    )
    assert response.status_code == 200
    data = response.json()
    empty_col = next(
        c for c in data["columns"] if c["observation_id"] == seeded_menu["obs_empty"]
    )
    assert empty_col["available"] is False
    assert empty_col["item_count"] == 0
