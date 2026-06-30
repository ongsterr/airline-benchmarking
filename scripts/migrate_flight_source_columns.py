"""Add flight_feature_sources metadata columns without full schema reset."""

from __future__ import annotations

from dotenv import load_dotenv

from backend.app.db.migrate import ensure_flight_source_columns
from backend.app.db.session import init_schema
from backend.app.models.entities import Base
from backend.app.db.session import engine


def main() -> None:
    load_dotenv()
    init_schema()
    Base.metadata.create_all(bind=engine)
    ensure_flight_source_columns()
    print("Migrated flight_feature_sources columns (page_type, cabin_keys, title).")


if __name__ == "__main__":
    main()
