"""FastAPI application entry point."""

import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.auth import (
    create_session_token,
    edit_auth_enabled,
    extract_bearer_token,
    require_edit_auth,
    validate_session_token,
    verify_password,
)

from backend.app.config import settings
from backend.app.db.migrate import (
    ensure_flight_source_columns,
    ensure_menu_columns,
    ensure_pipeline_run_columns,
)
from backend.app.db.session import engine, get_db, init_schema
from backend.app.models.entities import Base
from backend.app.routers import aircraft as aircraft_router
from backend.app.routers import airlines as airlines_router
from backend.app.routers import compare as compare_router
from backend.app.routers import export as export_router
from backend.app.routers import flight_features as flight_features_router
from backend.app.routers import menu as menu_router
from backend.app.routers import pipeline as pipeline_router
from shared.constants import MAX_COMPARE_CONFIGS
from shared.schemas import (
    AircraftConfigUpdate,
    AircraftDetailResponse,
    AircraftFilterOptions,
    AircraftListItem,
    AirlineFlightFeaturesUpdate,
    AirlineSummary,
    CabinFlightFeatures,
    CompareAirlineResponse,
    CompareResponse,
    MenuCompareResponse,
    MenuFilterOptionsResponse,
    PipelineRunResponse,
    PipelineTriggerRequest,
)

app = FastAPI(title="Flight Benchmarking API", version="0.1.0")


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str


class AuthMeResponse(BaseModel):
    authenticated: bool


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
    ensure_flight_source_columns()
    ensure_pipeline_run_columns()
    ensure_menu_columns()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/auth/login", response_model=LoginResponse)
def auth_login(body: LoginRequest) -> LoginResponse:
    if not edit_auth_enabled():
        raise HTTPException(status_code=503, detail="Edit authentication is not configured")
    if not verify_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    return LoginResponse(token=create_session_token())


@app.get("/api/v1/auth/me", response_model=AuthMeResponse)
def auth_me(authorization: str | None = Header(None)) -> AuthMeResponse:
    if not edit_auth_enabled():
        return AuthMeResponse(authenticated=True)
    token = extract_bearer_token(authorization)
    return AuthMeResponse(authenticated=bool(token and validate_session_token(token)))


@app.post("/api/v1/auth/logout")
def auth_logout() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/airlines/summary", response_model=list[AirlineSummary])
def airline_summary(db: Session = Depends(get_db)) -> list[AirlineSummary]:
    return airlines_router.get_airline_summaries(db)


@app.get("/api/v1/aircraft", response_model=dict)
def list_aircraft(
    airline: str | None = None,
    aircraft_type: str | None = None,
    haul_type: str | None = None,
    manufacturer: str | None = None,
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
        haul_type=haul_type,
        manufacturer=manufacturer,
        search=search,
        has_premium_economy=has_premium_economy,
        offset=offset,
        limit=limit,
    )
    return {"items": items, "total": total}


@app.get("/api/v1/aircraft/filter-options", response_model=AircraftFilterOptions)
def aircraft_filter_options(db: Session = Depends(get_db)) -> AircraftFilterOptions:
    return aircraft_router.get_aircraft_filter_options(db)


@app.get("/api/v1/aircraft/{svg_id}", response_model=AircraftDetailResponse)
def aircraft_detail(svg_id: str, db: Session = Depends(get_db)) -> AircraftDetailResponse:
    detail = aircraft_router.get_aircraft_detail(db, svg_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Aircraft configuration not found")
    slug = svg_id.split("-", 1)[0]
    flight_features = flight_features_router.get_flight_features_for_slug(db, slug)
    return AircraftDetailResponse(**detail.model_dump(), flight_features=flight_features)


@app.patch("/api/v1/aircraft/{svg_id}", response_model=AircraftDetailResponse)
def update_aircraft(
    svg_id: str,
    body: AircraftConfigUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_edit_auth),
) -> AircraftDetailResponse:
    try:
        detail = aircraft_router.update_aircraft_config(db, svg_id, body)
        db.commit()
    except LookupError:
        raise HTTPException(status_code=404, detail="Aircraft configuration not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    slug = svg_id.split("-", 1)[0]
    flight_features = flight_features_router.get_flight_features_for_slug(db, slug)
    return AircraftDetailResponse(**detail.model_dump(), flight_features=flight_features)


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


@app.get("/api/v1/compare/airlines", response_model=CompareAirlineResponse)
def compare_airlines(
    slugs: str = Query(..., description="Comma-separated airline slugs"),
    cabin: str | None = Query(None, description="Cabin class key: first, business, premium_economy, economy"),
    db: Session = Depends(get_db),
) -> CompareAirlineResponse:
    airline_slugs = [s.strip() for s in slugs.split(",") if s.strip()]
    if len(airline_slugs) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 airline slugs to compare")
    if len(airline_slugs) > MAX_COMPARE_CONFIGS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_COMPARE_CONFIGS} airlines for comparison",
        )
    return flight_features_router.compare_airlines(db, airline_slugs, cabin=cabin)


@app.get("/api/v1/menu/filter-options", response_model=MenuFilterOptionsResponse)
def menu_filter_options(
    cabin: str | None = Query(
        "business",
        description="Cabin class key: first, business, premium_economy, economy",
    ),
    item_type: str | None = Query(
        "all",
        description="Item type filter: food, beverage, or all",
    ),
    db: Session = Depends(get_db),
) -> MenuFilterOptionsResponse:
    try:
        return menu_router.get_menu_filter_options(db, cabin=cabin, item_type=item_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/menu/compare", response_model=MenuCompareResponse)
def menu_compare(
    observation_ids: str = Query(
        ...,
        description="Comma-separated menu observation UUIDs",
    ),
    cabin: str | None = Query(
        "business",
        description="Cabin class key: first, business, premium_economy, economy",
    ),
    item_type: str | None = Query(
        "all",
        description="Item type filter: food, beverage, or all",
    ),
    db: Session = Depends(get_db),
) -> MenuCompareResponse:
    try:
        ids = menu_router.parse_observation_ids(observation_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if len(ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="Provide at least 2 observation ids to compare",
        )
    if len(ids) > MAX_COMPARE_CONFIGS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_COMPARE_CONFIGS} menu observations for comparison",
        )
    try:
        return menu_router.compare_menus(
            db,
            observation_ids=ids,
            cabin=cabin,
            item_type=item_type,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/v1/airlines/{slug}/flight-features", response_model=CabinFlightFeatures)
def update_airline_flight_features(
    slug: str,
    body: AirlineFlightFeaturesUpdate,
    cabin: str = Query("business", description="Cabin class key: first, business, premium_economy, economy"),
    db: Session = Depends(get_db),
    _: None = Depends(require_edit_auth),
) -> CabinFlightFeatures:
    cabin_key = cabin.lower().replace(" ", "_")
    try:
        result = flight_features_router.update_airline_cabin_flight_features(
            db,
            slug,
            cabin_key,
            body,
            update_source_url="source_url" in body.model_fields_set,
        )
        db.commit()
    except LookupError:
        raise HTTPException(status_code=404, detail="Airline flight features not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@app.post("/api/v1/pipeline/hardware", response_model=PipelineRunResponse, status_code=202)
def trigger_hardware_pipeline(
    body: PipelineTriggerRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_edit_auth),
) -> PipelineRunResponse:
    return pipeline_router.trigger_hardware(db, body)


@app.post("/api/v1/pipeline/flight", response_model=PipelineRunResponse, status_code=202)
def trigger_flight_pipeline(
    body: PipelineTriggerRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_edit_auth),
) -> PipelineRunResponse:
    return pipeline_router.trigger_flight(db, body)


@app.get("/api/v1/pipeline/runs/active", response_model=PipelineRunResponse | None)
def get_active_pipeline_run(
    db: Session = Depends(get_db),
    _: None = Depends(require_edit_auth),
) -> PipelineRunResponse | None:
    active = pipeline_router.get_active_run(db)
    return pipeline_router.pipeline_run_to_response(active) if active else None


@app.get("/api/v1/pipeline/runs/{run_id}", response_model=PipelineRunResponse)
def get_pipeline_run(
    run_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_edit_auth),
) -> PipelineRunResponse:
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid run id") from exc
    run_record = pipeline_router.get_run_by_id(db, run_uuid)
    if not run_record:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return pipeline_router.pipeline_run_to_response(run_record)


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
