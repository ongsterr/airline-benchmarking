"""Pipeline trigger and status endpoints."""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.db.migrate import ensure_flight_source_columns
from backend.app.db.session import SessionLocal
from backend.app.models.entities import PipelineRun
from pipeline.run import execute_hardware_pipeline
from pipeline.run_flight import execute_flight_pipeline
from shared.schemas import PipelineRunResponse, PipelineRunStatus, PipelineTriggerRequest

logger = logging.getLogger(__name__)


def _run_status(run_record: PipelineRun) -> PipelineRunStatus:
    if run_record.finished_at is None:
        return "running"
    if run_record.errors:
        return "failed"
    return "completed"


def pipeline_run_to_response(run_record: PipelineRun) -> PipelineRunResponse:
    return PipelineRunResponse(
        id=str(run_record.id),
        pipeline_type=run_record.pipeline_type or "hardware",
        status=_run_status(run_record),
        started_at=run_record.started_at,
        finished_at=run_record.finished_at,
        airlines=run_record.airlines or [],
        configs_discovered=run_record.configs_discovered or 0,
        configs_updated=run_record.configs_updated or 0,
        configs_skipped=run_record.configs_skipped or 0,
        errors=run_record.errors,
    )


def _validate_airlines(airlines: list[str]) -> list[str]:
    cleaned = [a.strip().lower() for a in airlines if a.strip()]
    if not cleaned:
        raise HTTPException(status_code=400, detail="Provide at least one airline slug")
    return cleaned


def get_active_run(db: Session) -> PipelineRun | None:
    return (
        db.query(PipelineRun)
        .filter(PipelineRun.finished_at.is_(None))
        .order_by(PipelineRun.started_at.desc())
        .first()
    )


def get_run_by_id(db: Session, run_id: uuid.UUID) -> PipelineRun | None:
    return db.query(PipelineRun).filter(PipelineRun.id == run_id).first()


def _run_hardware_background(run_id: uuid.UUID, airlines: list[str], force: bool, skip_existing: bool) -> None:
    load_dotenv()
    ensure_flight_source_columns()
    db = SessionLocal()
    try:
        run_record = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not run_record:
            logger.error("Pipeline run %s not found", run_id)
            return
        try:
            execute_hardware_pipeline(db, run_record, airlines, force=force, skip_existing=skip_existing)
            db.commit()
        except Exception as exc:
            db.rollback()
            run_record = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
            if run_record:
                run_record.errors = [str(exc)]
                run_record.finished_at = datetime.now(timezone.utc)
                db.commit()
            logger.exception("Hardware pipeline failed for run %s", run_id)
    finally:
        db.close()


def _run_flight_background(run_id: uuid.UUID, airlines: list[str], force: bool, skip_existing: bool) -> None:
    load_dotenv()
    ensure_flight_source_columns()
    db = SessionLocal()
    try:
        run_record = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not run_record:
            logger.error("Pipeline run %s not found", run_id)
            return
        try:
            execute_flight_pipeline(db, run_record, airlines, force=force, skip_existing=skip_existing)
            db.commit()
        except Exception as exc:
            db.rollback()
            run_record = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
            if run_record:
                run_record.errors = [str(exc)]
                run_record.finished_at = datetime.now(timezone.utc)
                db.commit()
            logger.exception("Flight pipeline failed for run %s", run_id)
    finally:
        db.close()


def _start_pipeline(
    db: Session,
    pipeline_type: str,
    airlines: list[str],
    force: bool,
    skip_existing: bool,
    background_fn,
) -> PipelineRunResponse:
    active = get_active_run(db)
    if active:
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline run {active.id} is already in progress",
        )

    started = datetime.now(timezone.utc)
    run_record = PipelineRun(
        started_at=started,
        airlines=airlines,
        pipeline_type=pipeline_type,
    )
    db.add(run_record)
    db.commit()
    db.refresh(run_record)

    thread = threading.Thread(
        target=background_fn,
        args=(run_record.id, airlines, force, skip_existing),
        daemon=True,
    )
    thread.start()

    return pipeline_run_to_response(run_record)


def trigger_hardware(db: Session, body: PipelineTriggerRequest) -> PipelineRunResponse:
    airlines = _validate_airlines(body.airlines)
    return _start_pipeline(
        db,
        "hardware",
        airlines,
        body.force,
        body.skip_existing,
        _run_hardware_background,
    )


def trigger_flight(db: Session, body: PipelineTriggerRequest) -> PipelineRunResponse:
    airlines = _validate_airlines(body.airlines)
    return _start_pipeline(
        db,
        "flight",
        airlines,
        body.force,
        body.skip_existing,
        _run_flight_background,
    )
