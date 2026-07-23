"""Batch CLI: run Emirates F&B menu extraction for many flights from a JSON config."""

from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from backend.app.db.session import SessionLocal
from backend.app.models.entities import PipelineRun
from pipeline.config import REQUEST_DELAY_SECONDS, USER_AGENT
from pipeline.menu_config import MENU_AIRLINE_SLUG, MENU_CABIN_CODES, STANDARD_MENU_CABINS
from pipeline.menu_load import menu_capture_exists
from pipeline.run_menu import _bootstrap_menu_schema, execute_menu_pipeline, process_cabin
from pipeline.run_progress import flush_run_progress

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MenuBatchEntry:
    """One resolved flight route to extract."""

    service_date: date
    flight: str
    origin: str
    destination: str
    cabins: list[str]
    force: bool
    skip_existing: bool

    def label(self) -> str:
        return (
            f"{self.origin}-{self.destination} EK{self.flight} "
            f"{self.service_date.isoformat()} ({len(self.cabins)} cabin(s))"
        )


def _require_str(value: Any, field: str, index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"extractions[{index}]: '{field}' must be a non-empty string")
    return value.strip()


def _resolve_cabins(raw: Any, index: int) -> list[str]:
    if raw is None:
        return list(STANDARD_MENU_CABINS)
    if not isinstance(raw, list) or not raw:
        raise ValueError(
            f"extractions[{index}]: 'cabins' must be a non-empty list of cabin keys"
        )
    cabins = [str(c).strip().lower() for c in raw if str(c).strip()]
    if not cabins:
        raise ValueError(f"extractions[{index}]: 'cabins' must list at least one cabin")
    unknown = [c for c in cabins if c not in MENU_CABIN_CODES]
    if unknown:
        raise ValueError(
            f"extractions[{index}]: unknown cabin(s) {unknown}; "
            f"expected one of {list(MENU_CABIN_CODES)}"
        )
    return cabins


def _resolve_bool(raw: Any, field: str, default: bool, index: int) -> bool:
    if raw is None:
        return default
    if not isinstance(raw, bool):
        raise ValueError(f"extractions[{index}]: '{field}' must be a boolean")
    return raw


def parse_batch_config(payload: dict[str, Any]) -> list[MenuBatchEntry]:
    """Parse a batch config dict, merge defaults into each extraction, validate."""
    if not isinstance(payload, dict):
        raise ValueError("Config root must be a JSON object")

    defaults = payload.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise ValueError("'defaults' must be a JSON object when present")

    extractions = payload.get("extractions")
    if not isinstance(extractions, list) or not extractions:
        raise ValueError("'extractions' must be a non-empty JSON array")

    entries: list[MenuBatchEntry] = []
    for i, raw in enumerate(extractions):
        if not isinstance(raw, dict):
            raise ValueError(f"extractions[{i}]: each entry must be a JSON object")

        merged = {**defaults, **raw}

        date_str = _require_str(merged.get("date"), "date", i)
        try:
            service_date = date.fromisoformat(date_str)
        except ValueError as exc:
            raise ValueError(
                f"extractions[{i}]: 'date' must be YYYY-MM-DD (got {date_str!r})"
            ) from exc

        flight_raw = _require_str(merged.get("flight"), "flight", i)
        flight = flight_raw.upper().removeprefix("EK")
        origin = _require_str(merged.get("origin"), "origin", i).upper()
        destination = _require_str(merged.get("destination"), "destination", i).upper()
        cabins = _resolve_cabins(merged.get("cabins"), i)
        force = _resolve_bool(merged.get("force"), "force", False, i)
        skip_existing = _resolve_bool(
            merged.get("skip_existing"), "skip_existing", False, i
        )

        entries.append(
            MenuBatchEntry(
                service_date=service_date,
                flight=flight,
                origin=origin,
                destination=destination,
                cabins=cabins,
                force=force,
                skip_existing=skip_existing,
            )
        )

    return entries


def load_batch_config(path: Path) -> list[MenuBatchEntry]:
    """Load JSON config file and return validated batch entries."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Config root must be a JSON object")

    return parse_batch_config(payload)


def execute_menu_batch_pipeline(
    db,
    run_record: PipelineRun,
    entries: list[MenuBatchEntry],
    *,
    force_override: bool | None = None,
    skip_existing_override: bool | None = None,
) -> None:
    """
    Run menu extraction for all batch entries under one PipelineRun.

    Progress counters are cumulative across entries x cabins.
    """
    if not entries:
        raise ValueError("entries must be a non-empty list")

    run_record.airlines = [MENU_AIRLINE_SLUG]
    run_record.pipeline_type = "menu"

    total_cabins = sum(len(entry.cabins) for entry in entries)
    updated = 0
    skipped = 0
    errors: list[str] = []
    cabin_index = 0

    run_record.configs_discovered = total_cabins
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
        for entry in entries:
            force = force_override if force_override is not None else entry.force
            skip_existing = (
                skip_existing_override
                if skip_existing_override is not None
                else entry.skip_existing
            )
            flight_norm = entry.flight
            origin_u = entry.origin.upper()
            dest_u = entry.destination.upper()

            for cabin_norm in entry.cabins:
                cabin_code = MENU_CABIN_CODES[cabin_norm]
                label = (
                    f"{origin_u}-{dest_u} EK{flight_norm}/"
                    f"{entry.service_date.isoformat()}/{cabin_norm}"
                )
                cabin_index += 1

                if skip_existing and not force and menu_capture_exists(
                    db,
                    flight_number=flight_norm,
                    origin_iata=origin_u,
                    dest_iata=dest_u,
                    service_date=entry.service_date,
                    cabin_code=cabin_code,
                ):
                    logger.info("%s: skipped (already loaded)", label)
                    skipped += 1
                    run_record.configs_skipped = skipped
                    flush_run_progress(db, run_record)
                    if cabin_index < total_cabins:
                        time.sleep(REQUEST_DELAY_SECONDS)
                    continue

                logger.info("Extracting menu for %s", label)
                try:
                    with db.begin_nested():
                        status, detail = process_cabin(
                            db,
                            service_date=entry.service_date,
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
                        errors.append(f"{label}:empty")
                        logger.warning("%s: %s", label, detail)
                    else:
                        errors.append(f"{label}:{status}")
                        logger.warning(
                            "%s: %s", label, status if not detail else detail
                        )
                except Exception as exc:
                    logger.exception("Failed %s", label)
                    errors.append(f"{label}:{exc}")

                run_record.configs_updated = updated
                run_record.configs_skipped = skipped
                run_record.errors = errors or None
                flush_run_progress(db, run_record)

                if cabin_index < total_cabins:
                    time.sleep(REQUEST_DELAY_SECONDS)

    run_record.finished_at = datetime.now(timezone.utc)
    logger.info(
        "Batch pipeline done: %d updated, %d skipped, %d errors (of %d cabins)",
        updated,
        skipped,
        len(errors),
        total_cabins,
    )


def run_batch(
    entries: list[MenuBatchEntry],
    *,
    force_override: bool | None = None,
    skip_existing_override: bool | None = None,
    continue_on_error: bool = True,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Run menu extraction for each entry.

    Returns (succeeded, failed) counts.
    """
    if dry_run:
        logger.info("Dry run: %d extraction(s) resolved", len(entries))
        for i, entry in enumerate(entries):
            force = force_override if force_override is not None else entry.force
            skip = (
                skip_existing_override
                if skip_existing_override is not None
                else entry.skip_existing
            )
            logger.info(
                "  [%d] %s force=%s skip_existing=%s cabins=%s",
                i,
                entry.label(),
                force,
                skip,
                ",".join(entry.cabins),
            )
        return len(entries), 0

    logger.info("Loading environment…")
    load_dotenv()
    _bootstrap_menu_schema()

    succeeded = 0
    failed = 0
    failures: list[str] = []

    for i, entry in enumerate(entries):
        force = force_override if force_override is not None else entry.force
        skip_existing = (
            skip_existing_override
            if skip_existing_override is not None
            else entry.skip_existing
        )
        label = entry.label()
        logger.info("[%d/%d] Starting %s", i + 1, len(entries), label)

        db = SessionLocal()
        started = datetime.now(timezone.utc)
        run_record = PipelineRun(
            started_at=started,
            airlines=[MENU_AIRLINE_SLUG],
            pipeline_type="menu",
        )
        db.add(run_record)
        db.commit()
        db.refresh(run_record)
        run_id = run_record.id

        try:
            execute_menu_pipeline(
                db,
                run_record,
                service_date=entry.service_date,
                flight=entry.flight,
                origin=entry.origin,
                destination=entry.destination,
                cabins=entry.cabins,
                force=force,
                skip_existing=skip_existing,
            )
            db.commit()
            succeeded += 1
            logger.info("[%d/%d] OK: %s", i + 1, len(entries), label)
        except Exception as exc:
            db.rollback()
            failed_run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
            if failed_run:
                failed_run.errors = [str(exc)]
                failed_run.finished_at = datetime.now(timezone.utc)
                db.commit()

            failed += 1
            reason = f"{label}: {exc}"
            failures.append(reason)
            logger.exception("[%d/%d] FAILED: %s", i + 1, len(entries), label)
            if not continue_on_error:
                break
        finally:
            db.close()

    logger.info(
        "Batch done: %d succeeded, %d failed (of %d)",
        succeeded,
        failed,
        len(entries),
    )
    if failures:
        for reason in failures:
            logger.error("  failure: %s", reason)
    return succeeded, failed


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run Emirates onboard F&B menu extraction for many flights "
            "listed in a JSON config file"
        )
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to JSON config (see pipeline/menu_batch.example.json)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Override: re-fetch and re-extract even when capture already exists",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Override: skip cabins that already have a menu_captures row",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Abort the batch on the first failed extraction (default: continue)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved entries without hitting the network or database",
    )
    args = parser.parse_args()

    try:
        entries = load_batch_config(args.config)
    except ValueError as exc:
        parser.error(str(exc))

    force_override = True if args.force else None
    skip_existing_override = True if args.skip_existing else None

    succeeded, failed = run_batch(
        entries,
        force_override=force_override,
        skip_existing_override=skip_existing_override,
        continue_on_error=not args.stop_on_error,
        dry_run=args.dry_run,
    )
    if failed and not args.dry_run:
        raise SystemExit(1)
    if succeeded == 0 and not args.dry_run:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
