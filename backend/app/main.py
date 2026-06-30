"""FastAPI application entry point."""

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
from backend.app.db.migrate import ensure_flight_source_columns
from backend.app.db.session import engine, get_db, init_schema
from backend.app.models.entities import Base
from backend.app.routers import aircraft as aircraft_router
from backend.app.routers import airlines as airlines_router
from backend.app.routers import compare as compare_router
from backend.app.routers import export as export_router
from backend.app.routers import flight_features as flight_features_router
from shared.constants import MAX_COMPARE_CONFIGS
from shared.schemas import (
    AircraftConfigUpdate,
    AircraftDetailResponse,
    AircraftListItem,
    AirlineSummary,
    CompareAirlineResponse,
    CompareResponse,
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
