"""Upsert Emirates menu captures, observations, and items into Postgres."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.models.entities import MenuCapture, MenuItem, MenuObservation
from pipeline.load import get_or_create_airline
from pipeline.menu_config import (
    MENU_AIRLINE_IATA,
    MENU_AIRLINE_NAME,
    MENU_AIRLINE_SLUG,
    MENU_SOURCE_ID,
)
from shared.schemas import MenuExtraction


def menu_capture_exists(
    db: Session,
    *,
    flight_number: str,
    origin_iata: str,
    dest_iata: str,
    service_date: date,
    cabin_code: str,
) -> bool:
    return (
        db.query(MenuCapture)
        .filter(
            MenuCapture.flight_number == flight_number,
            MenuCapture.origin_iata == origin_iata.upper(),
            MenuCapture.dest_iata == dest_iata.upper(),
            MenuCapture.service_date == service_date,
            MenuCapture.cabin_code == cabin_code,
        )
        .count()
        > 0
    )


def _clear_enrichment(row: MenuItem) -> None:
    row.item_type = None
    row.beverage_type = None
    row.is_vegetarian = None
    row.is_vegan = None
    row.is_localized = None
    row.vegetarian_confidence = None
    row.vegan_confidence = None
    row.localization_confidence = None
    row.localization_note = None
    row.enrichment_version = None
    row.enriched_at = None


def _base_fields_equal(row: MenuItem, item) -> bool:
    return (
        (row.category or "") == (item.category or "")
        and (row.subcategory or "") == (item.subcategory or "")
        and (row.code or "") == (item.code or "")
        and (row.title or "") == (item.title or "")
        and (row.desc or None) == (item.desc or None)
    )


def upsert_menu_extraction(
    db: Session,
    *,
    extraction: MenuExtraction,
    cabin_code: str,
    flight_number: str,
    origin_iata: str,
    dest_iata: str,
    service_date: date,
    direction: str | None,
    source_url: str,
    captured_at: datetime,
    snapshot_path: Path | str | None,
    raw_bytes_size: int | None,
    http_status: int | None,
    extractor_version: str | None,
    extracted_at: datetime | None = None,
    default_tier: int = 1,
) -> tuple[MenuCapture, MenuObservation]:
    """Upsert capture + observation; reconcile items by item_hash, preserving enrichment."""
    airline = get_or_create_airline(
        db, MENU_AIRLINE_SLUG, MENU_AIRLINE_NAME, MENU_AIRLINE_IATA
    )
    origin = origin_iata.upper()
    dest = dest_iata.upper()
    flight = flight_number.lstrip("0") or flight_number
    ts = extracted_at or datetime.now(timezone.utc)
    snap = str(snapshot_path) if snapshot_path else None

    capture = (
        db.query(MenuCapture)
        .filter(
            MenuCapture.flight_number == flight,
            MenuCapture.origin_iata == origin,
            MenuCapture.dest_iata == dest,
            MenuCapture.service_date == service_date,
            MenuCapture.cabin_code == cabin_code,
        )
        .first()
    )

    capture_fields = {
        "source_id": MENU_SOURCE_ID,
        "airline_id": airline.id,
        "source_url": source_url,
        "cabin_code": cabin_code,
        "flight_number": flight,
        "origin_iata": origin,
        "dest_iata": dest,
        "service_date": service_date,
        "captured_at": captured_at,
        "snapshot_path": snap,
        "media_type": "application/json",
        "raw_bytes_size": raw_bytes_size,
        "http_status": http_status,
        "default_tier": default_tier,
    }

    if capture:
        for key, value in capture_fields.items():
            setattr(capture, key, value)
    else:
        capture = MenuCapture(**capture_fields)
        db.add(capture)
        db.flush()

    observation = (
        db.query(MenuObservation).filter(MenuObservation.capture_id == capture.id).first()
    )
    menu_cycle = extraction.menu_cycle or service_date.strftime("%Y-%m")
    obs_fields = {
        "capture_id": capture.id,
        "airline_id": airline.id,
        "cabin_norm": extraction.cabin_norm,
        "cabin_marketing": extraction.cabin_marketing,
        "origin_iata": origin,
        "dest_iata": dest,
        "direction": direction,
        "menu_cycle": menu_cycle,
        "service_date": service_date,
        "grain_observed": extraction.grain_observed or None,
        "confidence_tier": extraction.confidence_tier,
        "extractor_version": extractor_version,
        "extracted_at": ts,
    }

    if observation:
        for key, value in obs_fields.items():
            setattr(observation, key, value)
    else:
        observation = MenuObservation(**obs_fields)
        db.add(observation)
        db.flush()

    existing = {
        row.item_hash: row
        for row in db.query(MenuItem).filter(MenuItem.observation_id == observation.id).all()
    }
    seen_hashes: set[str] = set()

    for item in extraction.items:
        seen_hashes.add(item.item_hash)
        row = existing.get(item.item_hash)
        if row is None:
            db.add(
                MenuItem(
                    observation_id=observation.id,
                    category=item.category,
                    subcategory=item.subcategory,
                    code=item.code,
                    title=item.title,
                    desc=item.desc,
                    position=item.position,
                    item_hash=item.item_hash,
                    item_type=item.item_type,
                    beverage_type=item.beverage_type,
                    is_vegetarian=item.is_vegetarian,
                    is_vegan=item.is_vegan,
                    is_localized=item.is_localized,
                    vegetarian_confidence=item.vegetarian_confidence,
                    vegan_confidence=item.vegan_confidence,
                    localization_confidence=item.localization_confidence,
                    localization_note=item.localization_note,
                    enrichment_version=item.enrichment_version,
                    enriched_at=item.enriched_at,
                )
            )
            continue

        if not _base_fields_equal(row, item):
            _clear_enrichment(row)

        row.category = item.category
        row.subcategory = item.subcategory
        row.code = item.code
        row.title = item.title
        row.desc = item.desc
        row.position = item.position
        # Apply enrichment from extraction only when provided (e.g. re-run with enrich)
        if item.enriched_at is not None:
            row.item_type = item.item_type
            row.beverage_type = item.beverage_type
            row.is_vegetarian = item.is_vegetarian
            row.is_vegan = item.is_vegan
            row.is_localized = item.is_localized
            row.vegetarian_confidence = item.vegetarian_confidence
            row.vegan_confidence = item.vegan_confidence
            row.localization_confidence = item.localization_confidence
            row.localization_note = item.localization_note
            row.enrichment_version = item.enrichment_version
            row.enriched_at = item.enriched_at

    for item_hash, row in existing.items():
        if item_hash not in seen_hashes:
            db.delete(row)

    db.flush()
    return capture, observation
