"""Incremental schema migrations (additive columns, no full reset)."""

from __future__ import annotations

from sqlalchemy import text

from backend.app.config import settings
from backend.app.db.session import engine


def ensure_flight_source_columns() -> None:
    """Add Phase 2 flight_feature_sources metadata columns if missing."""
    schema = settings.db_schema
    stmts = [
        f'ALTER TABLE "{schema}".flight_feature_sources ADD COLUMN IF NOT EXISTS page_type VARCHAR(30)',
        f'ALTER TABLE "{schema}".flight_feature_sources ADD COLUMN IF NOT EXISTS cabin_keys JSONB',
        f'ALTER TABLE "{schema}".flight_feature_sources ADD COLUMN IF NOT EXISTS title VARCHAR(200)',
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))
