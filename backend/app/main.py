"""FastAPI application entry point."""

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.db.session import engine, get_db, init_schema
from backend.app.models.entities import Base
from backend.app.routers import aircraft as aircraft_router
from backend.app.routers import airlines as airlines_router
from backend.app.routers import compare as compare_router
from backend.app.routers import export as export_router
from shared.constants import MAX_COMPARE_CONFIGS
from shared.schemas import (
    AircraftConfigUpdate,
    AircraftConfiguration,
    AircraftListItem,
    AirlineSummary,
    CompareResponse,
)

app = FastAPI(title="Flight Benchmarking API", version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_schema()
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/airlines/summary", response_model=list[AirlineSummary])
def airline_summary(db: Session = Depends(get_db)) -> list[AirlineSummary]:
    return airlines_router.get_airline_summaries(db)


@app.get("/api/v1/aircraft", response_model=dict)
def list_aircraft(
    airline: str | None = None,
    aircraft_type: str | None = None,
    search: str | None = None,
    has_premium_economy: bool | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> dict:
    items, total = aircraft_router.list_aircraft(
        db,
        airline=airline,
        aircraft_type=aircraft_type,
        search=search,
        has_premium_economy=has_premium_economy,
        offset=offset,
        limit=limit,
    )
    return {"items": items, "total": total}


@app.get("/api/v1/aircraft/{svg_id}", response_model=AircraftConfiguration)
def aircraft_detail(svg_id: str, db: Session = Depends(get_db)) -> AircraftConfiguration:
    detail = aircraft_router.get_aircraft_detail(db, svg_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Aircraft configuration not found")
    return detail


@app.patch("/api/v1/aircraft/{svg_id}", response_model=AircraftConfiguration)
def update_aircraft(
    svg_id: str,
    body: AircraftConfigUpdate,
    db: Session = Depends(get_db),
) -> AircraftConfiguration:
    try:
        detail = aircraft_router.update_aircraft_config(db, svg_id, body)
        db.commit()
    except LookupError:
        raise HTTPException(status_code=404, detail="Aircraft configuration not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return detail


@app.get("/api/v1/compare", response_model=CompareResponse)
def compare(
    ids: str = Query(..., description="Comma-separated svg_ids"),
    cabin: str | None = Query(None, description="Cabin class key: first, business, premium_economy, economy"),
    db: Session = Depends(get_db),
) -> CompareResponse:
    svg_ids = [s.strip() for s in ids.split(",") if s.strip()]
    if len(svg_ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 aircraft ids to compare")
    if len(svg_ids) > MAX_COMPARE_CONFIGS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_COMPARE_CONFIGS} aircraft configs for comparison",
        )
    return compare_router.compare_aircraft(db, svg_ids, cabin=cabin)


@app.get("/api/v1/export.csv")
def export_csv(
    ids: str = Query(..., description="Comma-separated svg_ids"),
    db: Session = Depends(get_db),
) -> Response:
    svg_ids = [s.strip() for s in ids.split(",") if s.strip()]
    if not svg_ids:
        raise HTTPException(status_code=400, detail="Provide at least 1 aircraft id to export")
    content, filename = export_router.build_export_csv(svg_ids, db)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
