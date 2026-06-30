"""Add dual-deck columns to existing schema without full reset."""

from __future__ import annotations

from dotenv import load_dotenv
from sqlalchemy import text

from backend.app.config import settings
from backend.app.db.session import engine, init_schema


def main() -> None:
    load_dotenv()
    init_schema()
    schema = settings.db_schema
    stmts = [
        f'ALTER TABLE "{schema}".aircraft_configurations ADD COLUMN IF NOT EXISTS deck VARCHAR(10)',
        f'ALTER TABLE "{schema}".aircraft_configurations ADD COLUMN IF NOT EXISTS parent_svg_id VARCHAR(50)',
        f'ALTER TABLE "{schema}".aircraft_configurations ADD COLUMN IF NOT EXISTS deck_state VARCHAR(20)',
        f'ALTER TABLE "{schema}".aircraft_configurations ADD COLUMN IF NOT EXISTS decks JSONB',
        f'ALTER TABLE "{schema}".cabin_configurations ADD COLUMN IF NOT EXISTS deck VARCHAR(10)',
        f'CREATE INDEX IF NOT EXISTS ix_aircraft_configurations_parent_svg_id ON "{schema}".aircraft_configurations (parent_svg_id)',
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))
        conn.execute(
            text(f'ALTER TABLE "{schema}".cabin_configurations DROP CONSTRAINT IF EXISTS uq_aircraft_cabin')
        )
        conn.execute(
            text(f'ALTER TABLE "{schema}".cabin_configurations DROP CONSTRAINT IF EXISTS uq_aircraft_deck_cabin')
        )
        conn.execute(
            text(
                f'ALTER TABLE "{schema}".cabin_configurations '
                f'ADD CONSTRAINT uq_aircraft_deck_cabin UNIQUE (aircraft_id, deck, cabin_key)'
            )
        )
    print(f'Migrated schema "{schema}" with dual-deck columns.')


if __name__ == "__main__":
    main()
