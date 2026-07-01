"""Shared helpers for pipeline run progress tracking."""

from __future__ import annotations

from backend.app.models.entities import PipelineRun


def flush_run_progress(db, run_record: PipelineRun) -> None:
    """Persist in-flight pipeline counters so status polling can report progress."""
    db.add(run_record)
    db.commit()
