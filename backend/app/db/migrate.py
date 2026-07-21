"""Incremental schema migrations (additive columns, no full reset)."""

from __future__ import annotations

from sqlalchemy import text

from backend.app.config import settings
from backend.app.db.session import engine


def ensure_pipeline_run_columns() -> None:
    """Add pipeline_type column to pipeline_runs if missing."""
    schema = settings.db_schema
    stmt = (
        f'ALTER TABLE "{schema}".pipeline_runs '
        f"ADD COLUMN IF NOT EXISTS pipeline_type VARCHAR(20) DEFAULT 'hardware'"
    )
    with engine.begin() as conn:
        conn.execute(text(stmt))


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


def menu_tables_exist() -> bool:
    """True when menu_captures already exists in the configured schema."""
    schema = settings.db_schema
    check = text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = :schema AND table_name = 'menu_captures'"
    )
    with engine.connect() as conn:
        return conn.execute(check, {"schema": schema}).scalar() is not None


def ensure_menu_columns() -> None:
    """Additive safety for menu pipeline tables (create_all creates them; this covers upgrades)."""
    schema = settings.db_schema
    # Only alter when menu_captures already exists (fresh DBs rely on create_all).
    check = text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = :schema AND table_name = 'menu_captures'"
    )
    with engine.begin() as conn:
        exists = conn.execute(check, {"schema": schema}).scalar()
        if not exists:
            return

        add_stmts = [
            (
                f'ALTER TABLE "{schema}".menu_captures '
                f"ADD COLUMN IF NOT EXISTS default_tier INTEGER DEFAULT 1"
            ),
            (
                f'ALTER TABLE "{schema}".menu_observations '
                f"ADD COLUMN IF NOT EXISTS grain_observed JSONB"
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f"ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT ''"
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f"ADD COLUMN IF NOT EXISTS subcategory VARCHAR(100) DEFAULT ''"
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f"ADD COLUMN IF NOT EXISTS code VARCHAR(40) DEFAULT ''"
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f'ADD COLUMN IF NOT EXISTS title VARCHAR(300) DEFAULT \'\''
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f"ADD COLUMN IF NOT EXISTS \"desc\" TEXT"
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f"ADD COLUMN IF NOT EXISTS item_type VARCHAR(20)"
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f"ADD COLUMN IF NOT EXISTS beverage_type VARCHAR(20)"
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f"ADD COLUMN IF NOT EXISTS is_vegetarian BOOLEAN"
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f"ADD COLUMN IF NOT EXISTS is_vegan BOOLEAN"
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f"ADD COLUMN IF NOT EXISTS is_localized BOOLEAN"
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f"ADD COLUMN IF NOT EXISTS localization_confidence DOUBLE PRECISION"
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f"ADD COLUMN IF NOT EXISTS localization_note TEXT"
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f"ADD COLUMN IF NOT EXISTS enrichment_version VARCHAR(100)"
            ),
            (
                f'ALTER TABLE "{schema}".menu_items '
                f"ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ"
            ),
        ]
        for stmt in add_stmts:
            conn.execute(text(stmt))

        # Widen category if an older VARCHAR(30) column exists.
        try:
            conn.execute(
                text(
                    f'ALTER TABLE "{schema}".menu_items '
                    f"ALTER COLUMN category TYPE VARCHAR(100)"
                )
            )
        except Exception:
            # Column may already be the right type, or table freshly created.
            pass

        # Backfill new columns from legacy taxonomy/LLM columns when present.
        col_check = text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = 'menu_items'"
        )
        cols = {row[0] for row in conn.execute(col_check, {"schema": schema}).all()}

        if "item_name" in cols:
            conn.execute(
                text(
                    f'UPDATE "{schema}".menu_items '
                    f"SET title = COALESCE(NULLIF(title, ''), item_name) "
                    f"WHERE COALESCE(title, '') = ''"
                )
            )
        if "item_desc" in cols:
            conn.execute(
                text(
                    f'UPDATE "{schema}".menu_items '
                    f'SET "desc" = COALESCE("desc", item_desc) '
                    f'WHERE "desc" IS NULL'
                )
            )
        if "course" in cols:
            conn.execute(
                text(
                    f'UPDATE "{schema}".menu_items '
                    f"SET subcategory = COALESCE(NULLIF(subcategory, ''), course) "
                    f"WHERE COALESCE(subcategory, '') = ''"
                )
            )
        # Prefer code from item_hash prefix (m:CODE / b:CODE).
        conn.execute(
            text(
                f'UPDATE "{schema}".menu_items '
                f"SET code = CASE "
                f"WHEN COALESCE(code, '') = '' AND item_hash LIKE 'm:%' "
                f"THEN substring(item_hash from 3) "
                f"WHEN COALESCE(code, '') = '' AND item_hash LIKE 'b:%' "
                f"THEN substring(item_hash from 3) "
                f"ELSE code END"
            )
        )

        # Drop obsolete columns (ignore if already gone).
        # Keep is_vegetarian / is_vegan — reused by enrichment.
        drop_cols = (
            "course",
            "item_name",
            "item_desc",
            "is_alcoholic",
            "source_span",
            "grounding_method",
            "grounding_score",
        )
        for col in drop_cols:
            if col in cols:
                conn.execute(
                    text(f'ALTER TABLE "{schema}".menu_items DROP COLUMN IF EXISTS {col}')
                )
