"""Emirates F&B menu extraction pipeline CLI orchestrator."""

from __future__ import annotations

import argparse
import logging
import time
from datetime import date, datetime, timezone

import httpx
from dotenv import load_dotenv

from backend.app.db.migrate import ensure_menu_columns, menu_tables_exist
from backend.app.db.session import SessionLocal, init_schema
from backend.app.models.entities import Base, PipelineRun
from pipeline.config import REQUEST_DELAY_SECONDS, USER_AGENT
from pipeline.menu_artifacts import save_menu_artifacts
from pipeline.menu_config import (
    MENU_AIRLINE_SLUG,
    MENU_CABIN_CODES,
    MENU_HUB_IATA,
    STANDARD_MENU_CABINS,
)
from pipeline.menu_enrich import enrich_observation_items
from pipeline.menu_extract import extract_menu_from_api
from pipeline.menu_fetch import fetch_menu_api
from pipeline.menu_load import menu_capture_exists, upsert_menu_extraction
from pipeline.run_progress import flush_run_progress

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _bootstrap_menu_schema() -> None:
    """Connect to DB and ensure menu tables/columns without redundant create_all."""
    from backend.app.db.session import engine

    logger.info("Connecting to database…")
    init_schema()

    if menu_tables_exist():
        logger.info("Menu tables present; applying column upgrades only")
        ensure_menu_columns()
    else:
        logger.info("Menu tables missing; creating schema via create_all")
        Base.metadata.create_all(bind=engine)
        ensure_menu_columns()
    logger.info("Database schema ready")


def _normalize_flight(flight: str) -> str:
    return flight.strip().lstrip("0") or flight.strip()


def derive_direction(origin: str, hub: str = MENU_HUB_IATA) -> str:
    """Outbound if departing Emirates hub (DXB); otherwise inbound."""
    return "outbound" if origin.upper() == hub.upper() else "inbound"


def process_cabin(
    db,
    *,
    service_date: date,
    flight: str,
    origin: str,
    destination: str,
    cabin_norm: str,
    client: httpx.Client,
) -> tuple[str, str | None]:
    """Fetch API + map + load one cabin. Returns (status, detail)."""
    cabin_code = MENU_CABIN_CODES[cabin_norm]
    direction = derive_direction(origin)
    flight_norm = _normalize_flight(flight)

    fetch_result = fetch_menu_api(
        service_date, flight_norm, origin, destination, cabin_norm, client=client
    )
    if fetch_result.error:
        return "fetch_error", fetch_result.error
    if fetch_result.empty_or_missing or not fetch_result.api_payload:
        return "skipped_missing", f"menu unavailable (http={fetch_result.status_code})"

    extract_result = extract_menu_from_api(
        fetch_result.api_payload,
        cabin_norm=cabin_norm,
        service_date=service_date,
    )

    extracted_at = datetime.now(timezone.utc)

    if extract_result.source == "empty" and not extract_result.extraction.items:
        save_menu_artifacts(
            origin=origin,
            destination=destination,
            flight=flight_norm,
            service_date=service_date.isoformat(),
            cabin_code=cabin_code,
            extraction=extract_result.extraction.model_dump(),
            source=extract_result.source,
            extractor_version=extract_result.extractor_version,
            source_url=fetch_result.source_url,
            snapshot_path=str(fetch_result.snapshot_path) if fetch_result.snapshot_path else None,
            extracted_at=extracted_at,
            llm_parsed=extract_result.llm_parsed,
        )
        return "empty", "no items extracted"

    _capture, observation = upsert_menu_extraction(
        db,
        extraction=extract_result.extraction,
        cabin_code=cabin_code,
        flight_number=flight_norm,
        origin_iata=origin,
        dest_iata=destination,
        service_date=service_date,
        direction=direction,
        source_url=fetch_result.source_url,
        captured_at=fetch_result.captured_at,
        snapshot_path=fetch_result.snapshot_path,
        raw_bytes_size=fetch_result.raw_bytes_size,
        http_status=fetch_result.status_code,
        extractor_version=extract_result.extractor_version,
        extracted_at=extracted_at,
    )

    enrich_result = enrich_observation_items(db, observation)
    logger.info(
        "%s-%s EK%s/%s enrichment: candidates=%d enriched=%d skipped=%d source=%s",
        origin.upper(),
        destination.upper(),
        flight_norm,
        cabin_norm,
        enrich_result.candidates,
        enrich_result.enriched,
        enrich_result.skipped_invalid,
        enrich_result.source,
    )

    enrichment_parsed = None
    if enrich_result.llm_batches:
        enrichment_parsed = {
            "source": enrich_result.source,
            "enrichment_version": enrich_result.enrichment_version,
            "candidates": enrich_result.candidates,
            "enriched": enrich_result.enriched,
            "skipped_invalid": enrich_result.skipped_invalid,
            "batches": enrich_result.llm_batches,
        }

    save_menu_artifacts(
        origin=origin,
        destination=destination,
        flight=flight_norm,
        service_date=service_date.isoformat(),
        cabin_code=cabin_code,
        extraction=extract_result.extraction.model_dump(),
        source=extract_result.source,
        extractor_version=extract_result.extractor_version,
        source_url=fetch_result.source_url,
        snapshot_path=str(fetch_result.snapshot_path) if fetch_result.snapshot_path else None,
        extracted_at=extracted_at,
        llm_parsed=extract_result.llm_parsed,
        enrichment_parsed=enrichment_parsed,
    )

    item_count = len(extract_result.extraction.items)
    return (
        "ok",
        (
            f"updated {item_count} item(s) (source={extract_result.source}; "
            f"enriched={enrich_result.enriched}/{enrich_result.candidates})"
        ),
    )


def execute_menu_pipeline(
    db,
    run_record: PipelineRun,
    *,
    service_date: date,
    flight: str,
    origin: str,
    destination: str,
    cabins: list[str] | None = None,
    force: bool = False,
    skip_existing: bool = False,
) -> None:
    """Run Emirates menu extraction for each cabin and update pipeline_runs progress."""
    cabin_list = cabins or list(STANDARD_MENU_CABINS)
    for cabin in cabin_list:
        if cabin not in MENU_CABIN_CODES:
            raise ValueError(f"Unknown cabin '{cabin}'; expected one of {list(MENU_CABIN_CODES)}")

    flight_norm = _normalize_flight(flight)
    origin_u = origin.upper()
    dest_u = destination.upper()

    run_record.airlines = [MENU_AIRLINE_SLUG]
    run_record.pipeline_type = "menu"

    updated = 0
    skipped = 0
    errors: list[str] = []

    run_record.configs_discovered = len(cabin_list)
    run_record.configs_updated = updated
    run_record.configs_skipped = skipped
    run_record.errors = None
    flush_run_progress(db, run_record)

    with httpx.Client(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.emirates.com",
        },
        follow_redirects=True,
        timeout=45,
    ) as client:
        for i, cabin_norm in enumerate(cabin_list):
            cabin_code = MENU_CABIN_CODES[cabin_norm]
            label = f"{origin_u}-{dest_u} EK{flight_norm}/{cabin_norm}"

            if skip_existing and not force and menu_capture_exists(
                db,
                flight_number=flight_norm,
                origin_iata=origin_u,
                dest_iata=dest_u,
                service_date=service_date,
                cabin_code=cabin_code,
            ):
                logger.info("%s: skipped (already loaded)", label)
                skipped += 1
                run_record.configs_skipped = skipped
                flush_run_progress(db, run_record)
                continue

            logger.info("Extracting menu for %s", label)
            try:
                with db.begin_nested():
                    status, detail = process_cabin(
                        db,
                        service_date=service_date,
                        flight=flight_norm,
                        origin=origin_u,
                        destination=dest_u,
                        cabin_norm=cabin_norm,
                        client=client,
                    )
                if status == "ok":
                    updated += 1
                    logger.info("%s: %s", label, detail)
                elif status in ("skipped_missing",):
                    skipped += 1
                    logger.info("%s: %s", label, detail)
                elif status == "empty":
                    errors.append(f"{cabin_norm}:empty")
                    logger.warning("%s: %s", label, detail)
                else:
                    errors.append(f"{cabin_norm}:{status}")
                    logger.warning("%s: %s", label, status if not detail else detail)
            except Exception as exc:
                logger.exception("Failed %s", label)
                errors.append(f"{cabin_norm}:{exc}")

            run_record.configs_updated = updated
            run_record.configs_skipped = skipped
            run_record.errors = errors or None
            flush_run_progress(db, run_record)

            if i < len(cabin_list) - 1:
                time.sleep(REQUEST_DELAY_SECONDS)

    run_record.finished_at = datetime.now(timezone.utc)
    logger.info("Done: %d updated, %d skipped, %d errors", updated, skipped, len(errors))


def run(
    *,
    service_date: date,
    flight: str,
    origin: str,
    destination: str,
    cabins: list[str] | None = None,
    force: bool = False,
    skip_existing: bool = False,
) -> None:
    logger.info("Loading environment…")
    load_dotenv()
    _bootstrap_menu_schema()

    db = SessionLocal()
    started = datetime.now(timezone.utc)
    run_record = PipelineRun(
        started_at=started,
        airlines=[MENU_AIRLINE_SLUG],
        pipeline_type="menu",
    )
    db.add(run_record)
    db.flush()

    cabin_list = cabins or list(STANDARD_MENU_CABINS)
    logger.info(
        "Starting menu extraction for %s-%s EK%s (%d cabin(s))",
        origin.upper(),
        destination.upper(),
        flight.strip().lstrip("0") or flight.strip(),
        len(cabin_list),
    )

    try:
        execute_menu_pipeline(
            db,
            run_record,
            service_date=service_date,
            flight=flight,
            origin=origin,
            destination=destination,
            cabins=cabins,
            force=force,
            skip_existing=skip_existing,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Emirates onboard F&B menu extraction pipeline"
    )
    parser.add_argument("--date", required=True, help="Service date YYYY-MM-DD")
    parser.add_argument("--flight", required=True, help="Flight number (e.g. 7 or EK7)")
    parser.add_argument("--origin", required=True, help="Origin IATA (e.g. DXB)")
    parser.add_argument("--destination", required=True, help="Destination IATA (e.g. LHR)")
    parser.add_argument(
        "--cabins",
        default=",".join(STANDARD_MENU_CABINS),
        help=f"Comma-separated cabin keys (default: {','.join(STANDARD_MENU_CABINS)})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch and re-extract even when capture already exists",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip cabins that already have a menu_captures row",
    )
    args = parser.parse_args()

    service_date = date.fromisoformat(args.date)
    flight = args.flight.upper().removeprefix("EK")
    cabins = [c.strip().lower() for c in args.cabins.split(",") if c.strip()]
    run(
        service_date=service_date,
        flight=flight,
        origin=args.origin,
        destination=args.destination,
        cabins=cabins,
        force=args.force,
        skip_existing=args.skip_existing,
    )


if __name__ == "__main__":
    main()
