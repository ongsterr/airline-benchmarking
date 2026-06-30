"""Pipeline CLI orchestrator."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv

from backend.app.db.session import SessionLocal, init_schema
from backend.app.models.entities import PipelineRun
from pipeline.artifacts import save_artifacts
from pipeline.config import DEFAULT_AIRLINES
from pipeline.deck import is_dual_deck_parent
from pipeline.discover import airline_display_name, discover_all
from pipeline.fetch import fetch_config_html, load_cached_html
from pipeline.load import get_existing_svg_ids, upsert_aircraft
from pipeline.normalize import normalize_with_llm
from pipeline.parse_json import extract_aircraft_json

import httpx
from pipeline.config import USER_AGENT

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def process_config(
    svg_id: str,
    slug: str,
    force: bool,
    client: httpx.Client,
    db,
) -> tuple[str, str | None]:
    """Process a single config. Returns (status, detail_message)."""
    airline_name = airline_display_name(slug)
    html = None
    fetched_at = datetime.now(timezone.utc)

    if not force:
        html = load_cached_html(svg_id)

    if html is None:
        result = fetch_config_html(svg_id, client)
        if result.error or not result.html_path:
            return "fetch_error", str(result.error)
        html = result.html_path.read_text(encoding="utf-8")
        fetched_at = result.fetched_at

    raw = extract_aircraft_json(html)
    if not raw:
        return "parse_error", None

    norm_result = normalize_with_llm(raw, slug, airline_name)
    save_artifacts(
        svg_id,
        raw,
        norm_result.aircraft,
        norm_result.source,
        llm_parsed=norm_result.llm_parsed,
        dropped_fields=norm_result.dropped_fields,
        cleaned_raw=norm_result.cleaned_raw,
    )

    if is_dual_deck_parent(svg_id, raw):
        return "skipped_parent", "dual-deck parent overview (deck pages are canonical)"

    upsert_aircraft(db, slug, norm_result.aircraft, fetched_at)
    detail = f"updated (source={norm_result.source})"
    return "ok", detail


def run(
    airlines: list[str],
    force: bool = False,
    limit: int = 0,
    skip_existing: bool = False,
) -> None:
    load_dotenv()
    init_schema()

    from backend.app.db.session import engine
    from backend.app.models.entities import Base

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    started = datetime.now(timezone.utc)
    run_record = PipelineRun(started_at=started, airlines=airlines)
    db.add(run_record)
    db.flush()

    discovered = discover_all(airlines)
    all_configs: list[tuple[str, str]] = []
    for slug, configs in discovered.items():
        logger.info("Discovered %d configs for %s", len(configs), slug)
        for svg_id in configs:
            all_configs.append((slug, svg_id))

    run_record.configs_discovered = len(all_configs)
    errors: list[str] = []
    updated = 0
    skipped = 0

    configs_to_process = all_configs[:limit] if limit > 0 else all_configs
    existing_svg_ids: set[str] = set()
    if skip_existing and not force:
        existing_svg_ids = get_existing_svg_ids(
            db, [svg_id for _, svg_id in configs_to_process]
        )

    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30) as client:
        for slug, svg_id in configs_to_process:
            if skip_existing and not force and svg_id in existing_svg_ids:
                logger.info("%s: skipped (already loaded)", svg_id)
                skipped += 1
                continue

            logger.info("Processing %s", svg_id)
            try:
                status, detail = process_config(svg_id, slug, force, client, db)
                if status == "ok":
                    updated += 1
                    logger.info("%s: %s", svg_id, detail)
                elif status == "skipped_parent":
                    skipped += 1
                    logger.info("%s: %s", svg_id, detail)
                else:
                    errors.append(f"{svg_id}:{status}")
                    logger.warning("%s: %s", svg_id, status)
            except Exception as exc:
                db.rollback()
                logger.exception("Failed %s", svg_id)
                errors.append(f"{svg_id}:{exc}")

    run_record.configs_updated = updated
    run_record.configs_skipped = skipped
    run_record.errors = errors or None
    run_record.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.close()

    logger.info("Done: %d updated, %d skipped (already loaded), %d errors", updated, skipped, len(errors))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run aircraft hardware extraction pipeline")
    parser.add_argument(
        "--airlines",
        default=",".join(DEFAULT_AIRLINES),
        help="Comma-separated airline slugs (default: ek,ba,ai)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch HTML from AeroLOPA (bypass cache); overrides --skip-existing",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip fetch/parse/normalize for configs already in the database",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max configs to process (0 = all)")
    args = parser.parse_args()
    airlines = [a.strip() for a in args.airlines.split(",") if a.strip()]
    run(airlines, force=args.force, limit=args.limit, skip_existing=args.skip_existing)


if __name__ == "__main__":
    main()
