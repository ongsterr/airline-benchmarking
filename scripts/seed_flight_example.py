"""Seed example flight features from output.py (no network)."""

from __future__ import annotations

from datetime import datetime, timezone

from dotenv import load_dotenv

from backend.app.db.session import SessionLocal, init_schema
from backend.app.models.entities import Base
from output import aircraft_flight_features
from pipeline.flight_load import upsert_flight_features
from shared.schemas import AirlineFlightFeatures, CabinFlightFeatures


def main() -> None:
    load_dotenv()
    init_schema()
    from backend.app.db.session import engine

    Base.metadata.create_all(bind=engine)

    cabins = {}
    for key, data in aircraft_flight_features.items():
        features = data.get("features", {})
        cabins[key] = CabinFlightFeatures(
            cabin_class=data.get("cabin_class", key.replace("_", " ").title()),
            check_in_priority=features.get("check-in_priority") or features.get("check_in_priority"),
            cabin_bag_pieces=features.get("cabin_bag_pieces"),
            cabin_bag_kg_per_piece=features.get("cabin_bag_kg_per_piece"),
            cabin_bag_kg_total=features.get("cabin_bag_kg_total"),
            checked_bag_pieces=features.get("checked_bag_pieces"),
            checked_bag_kg_per_piece=features.get("checked_bag_kg_per_piece"),
            checked_bag_kg_total=features.get("checked_bag_kg_total"),
            boarding_priority=features.get("boarding_priority"),
            lounge_access=features.get("lounge_access"),
            amenity_kit=features.get("amenity_kit"),
            amenity_kit_brand=features.get("amenity_kit_brand"),
        )

    db = SessionLocal()
    upsert_flight_features(
        db,
        "ek",
        "Emirates",
        "EK",
        AirlineFlightFeatures(cabins=cabins),
        "https://www.emirates.com/uk/english/before-you-fly/baggage/",
        datetime.now(timezone.utc),
    )
    db.commit()
    db.close()
    print("Seeded Emirates flight features from output.py example.")


if __name__ == "__main__":
    main()
