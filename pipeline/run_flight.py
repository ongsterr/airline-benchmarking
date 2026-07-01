"""Flight features pipeline CLI orchestrator."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv

from backend.app.db.migrate import ensure_flight_source_columns
from backend.app.db.session import SessionLocal, init_schema
from backend.app.models.entities import Base, PipelineRun
from pipeline.discover import airline_display_name
from pipeline.flight_artifacts import save_flight_artifacts
from pipeline.flight_config import DEFAULT_AIRLINES
from pipeline.flight_load import airline_has_flight_features, upsert_flight_features, upsert_flight_sources
from pipeline.flight_research import (
    extract_grounding_queries,
    merge_sources_for_upsert,
    primary_source_url,
    research_flight_features,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

IATA_BY_SLUG = {"ek": "EK", "ba": "BA", "ai": "AI"}


def process_airline(slug: str, db) -> tuple[str, str | None]:
    airline_name = airline_display_name(slug)
    result = research_flight_features(slug, airline_name)

    sources_for_db = merge_sources_for_upsert(
        result.sources_by_cabin,
        result.grounding_candidates,
    )
    sources_by_cabin_meta = {
        cabin: [s.model_dump() for s in sources]
        for cabin, sources in result.sources_by_cabin.items()
    }
    grounding_queries = extract_grounding_queries(result.grounding_metadata)

    features_dict = result.features.model_dump()
    save_flight_artifacts(
        slug,
        features_dict,
        result.source,
        llm_parsed=result.llm_parsed,
        research_model=result.research_model,
        researched_at=result.researched_at,
        sources_by_cabin=sources_by_cabin_meta or None,
        grounding_queries=grounding_queries or None,
    )

    if not result.features.cabins:
        return "empty", "no cabin features researched"

    upsert_flight_sources(db, slug, airline_name, IATA_BY_SLUG.get(slug), sources_for_db)
    upsert_flight_features(
        db,
        slug,
        airline_name,
        IATA_BY_SLUG.get(slug),
        result.features,
        primary_source_url(sources_for_db),
        result.researched_at,
    )
    source_count = len(sources_for_db)
    return (
        "ok",
        f"updated {len(result.features.cabins)} cabin(s) from {source_count} source(s) "
        f"(source={result.source}, model={result.research_model})",
    )


def execute_flight_pipeline(
    db,
    run_record: PipelineRun,
    airlines: list[str],
    force: bool = False,
    skip_existing: bool = False,
) -> None:
    """Run flight features research for airlines and update the given pipeline run record."""
    run_record.airlines = airlines
    run_record.pipeline_type = "flight"

    updated = 0
    skipped = 0
    errors: list[str] = []

    for slug in airlines:
        if skip_existing and not force and airline_has_flight_features(db, slug):
            logger.info("%s: skipped (already loaded)", slug)
            skipped += 1
            continue

        logger.info("Researching flight features for %s", slug)
        try:
            with db.begin_nested():
                status, detail = process_airline(slug, db)
            if status == "ok":
                updated += 1
                logger.info("%s: %s", slug, detail)
            elif status == "empty":
                errors.append(f"{slug}:empty")
                logger.warning("%s: %s", slug, detail)
            else:
                errors.append(f"{slug}:{status}")
                logger.warning("%s: %s", slug, status)
        except Exception as exc:
            logger.exception("Failed %s", slug)
            errors.append(f"{slug}:{exc}")

    run_record.configs_discovered = len(airlines)
    run_record.configs_updated = updated
    run_record.configs_skipped = skipped
    run_record.errors = errors or None
    run_record.finished_at = datetime.now(timezone.utc)

    logger.info("Done: %d updated, %d skipped, %d errors", updated, skipped, len(errors))


def run(
    airlines: list[str],
    force: bool = False,
    skip_existing: bool = False,
) -> None:
    load_dotenv()
    init_schema()

    from backend.app.db.session import engine

    Base.metadata.create_all(bind=engine)
    ensure_flight_source_columns()

    db = SessionLocal()
    started = datetime.now(timezone.utc)
    run_record = PipelineRun(started_at=started, airlines=airlines, pipeline_type="flight")
    db.add(run_record)
    db.flush()

    try:
        execute_flight_pipeline(db, run_record, airlines, force, skip_existing)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run cabin flight features research pipeline")
    parser.add_argument(
        "--airlines",
        default=",".join(DEFAULT_AIRLINES),
        help="Comma-separated airline slugs (default: ek,ba,ai)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run LLM research even when airline already has flight features in DB",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip airlines that already have flight features in the database",
    )
    args = parser.parse_args()
    airlines = [a.strip() for a in args.airlines.split(",") if a.strip()]
    run(airlines, force=args.force, skip_existing=args.skip_existing)


if __name__ == "__main__":
    main()
