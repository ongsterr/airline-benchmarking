"""Menu filter-options and comparison endpoints."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session, joinedload

from backend.app.models.entities import MenuCapture, MenuItem, MenuObservation
from shared.constants import is_display_menu_capture
from shared.schemas import (
    MenuCabinNorm,
    MenuCompareColumn,
    MenuCompareDetailRow,
    MenuCompareItemDetail,
    MenuCompareResponse,
    MenuCompareSummaryRow,
    MenuFilterOptionsResponse,
    MenuFlightOption,
    MenuItemType,
    MenuMetricCounts,
)

CABIN_ORDER: list[str] = ["first", "business", "premium_economy", "economy"]
VALID_CABINS: set[str] = set(CABIN_ORDER)
VALID_ITEM_TYPES: set[str] = {"food", "beverage", "all"}


def _normalize_cabin(cabin: str | None) -> MenuCabinNorm:
    key = (cabin or "business").lower().replace(" ", "_")
    if key not in VALID_CABINS:
        raise ValueError(
            "Invalid cabin; expected one of: first, business, premium_economy, economy"
        )
    return key  # type: ignore[return-value]


def _normalize_item_type(item_type: str | None) -> MenuItemType | None:
    if item_type is None or item_type == "" or item_type == "all":
        return None
    key = item_type.lower().replace("-", "_")
    if key not in {"food", "beverage"}:
        raise ValueError("Invalid item_type; expected one of: food, beverage, all")
    return key  # type: ignore[return-value]


def parse_observation_ids(raw: str) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        try:
            oid = uuid.UUID(token)
        except ValueError as exc:
            raise ValueError(f"Invalid observation id: {token}") from exc
        if oid in seen:
            continue
        seen.add(oid)
        ids.append(oid)
    return ids


def _flight_label(
    *,
    flight_number: str,
    origin_iata: str,
    dest_iata: str,
    service_date: date,
) -> str:
    return f"EK {flight_number} {origin_iata}→{dest_iata} {service_date.isoformat()}"


def _item_matches_type(item: MenuItem, item_type: MenuItemType | None) -> bool:
    if item_type is None:
        return True
    return item.item_type == item_type


def _is_observation_available(observation: MenuObservation, filtered_items: list[MenuItem]) -> bool:
    """Empty/unavailable menus (tier 3 or no items) are distinct from a zero metric count."""
    if observation.confidence_tier >= 3:
        return False
    return len(filtered_items) > 0 or len(observation.items) > 0


def _metric_counts(items: list[MenuItem]) -> MenuMetricCounts:
    alcoholic = 0
    non_alcoholic = 0
    vegetarian = 0
    vegan = 0
    localized = 0
    enriched = 0
    for item in items:
        if item.enriched_at is not None:
            enriched += 1
        if item.beverage_type == "alcoholic":
            alcoholic += 1
        elif item.beverage_type == "non_alcoholic":
            non_alcoholic += 1
        if item.is_vegetarian is True:
            vegetarian += 1
        if item.is_vegan is True:
            vegan += 1
        if item.is_localized is True:
            localized += 1
    return MenuMetricCounts(
        alcoholic=alcoholic,
        non_alcoholic=non_alcoholic,
        vegetarian=vegetarian,
        vegan=vegan,
        localized=localized,
        total_items=len(items),
        enriched_items=enriched,
    )


def _to_detail(item: MenuItem) -> MenuCompareItemDetail:
    return MenuCompareItemDetail(
        code=item.code or "",
        title=item.title or "",
        desc=item.desc,
        position=item.position or 1,
        item_hash=item.item_hash or "",
        item_type=item.item_type,  # type: ignore[arg-type]
        beverage_type=item.beverage_type,  # type: ignore[arg-type]
        is_vegetarian=item.is_vegetarian,
        is_vegan=item.is_vegan,
        is_localized=item.is_localized,
        enriched=item.enriched_at is not None,
    )


def _build_option(
    observation: MenuObservation,
    capture: MenuCapture,
    *,
    item_type: MenuItemType | None,
) -> MenuFlightOption:
    filtered = [i for i in observation.items if _item_matches_type(i, item_type)]
    origin = capture.origin_iata or observation.origin_iata or ""
    dest = capture.dest_iata or observation.dest_iata or ""
    service = capture.service_date or observation.service_date
    assert service is not None
    return MenuFlightOption(
        observation_id=str(observation.id),
        flight_number=capture.flight_number,
        origin_iata=origin,
        dest_iata=dest,
        service_date=service,
        cabin_norm=observation.cabin_norm,  # type: ignore[arg-type]
        cabin_marketing=observation.cabin_marketing,
        label=_flight_label(
            flight_number=capture.flight_number,
            origin_iata=origin,
            dest_iata=dest,
            service_date=service,
        ),
        item_count=len(filtered),
        available=_is_observation_available(observation, filtered),
    )


def get_menu_filter_options(
    db: Session,
    *,
    cabin: str | None = None,
    item_type: str | None = None,
) -> MenuFilterOptionsResponse:
    cabin_key = _normalize_cabin(cabin)
    type_key = _normalize_item_type(item_type)

    distinct_cabins = [
        row[0]
        for row in db.query(MenuObservation.cabin_norm)
        .distinct()
        .order_by(MenuObservation.cabin_norm)
        .all()
        if row[0] in VALID_CABINS
    ]

    observations = (
        db.query(MenuObservation)
        .options(
            joinedload(MenuObservation.capture).joinedload(MenuCapture.airline),
            joinedload(MenuObservation.items),
        )
        .filter(MenuObservation.cabin_norm == cabin_key)
        .all()
    )

    options: list[MenuFlightOption] = []
    for obs in observations:
        capture = obs.capture
        if capture is None:
            continue
        airline_slug = capture.airline.slug if capture.airline is not None else None
        if not is_display_menu_capture(
            airline_slug=airline_slug,
            source_url=capture.source_url,
        ):
            continue
        option = _build_option(obs, capture, item_type=type_key)
        if type_key is not None and option.item_count == 0 and option.available:
            # Still include available observations with zero matching items so
            # users can see empty food/beverage coverage for that flight.
            pass
        options.append(option)

    options.sort(
        key=lambda o: (o.service_date, o.flight_number, o.origin_iata, o.dest_iata)
    )

    return MenuFilterOptionsResponse(
        cabins=sorted(  # type: ignore[arg-type]
            distinct_cabins,
            key=lambda c: CABIN_ORDER.index(c) if c in CABIN_ORDER else 99,
        ),
        observations=options,
    )


def compare_menus(
    db: Session,
    *,
    observation_ids: list[uuid.UUID],
    cabin: str | None = None,
    item_type: str | None = None,
) -> MenuCompareResponse:
    cabin_key = _normalize_cabin(cabin)
    type_key = _normalize_item_type(item_type)

    observations = (
        db.query(MenuObservation)
        .options(
            joinedload(MenuObservation.capture),
            joinedload(MenuObservation.items),
        )
        .filter(MenuObservation.id.in_(observation_ids))
        .all()
    )
    by_id = {obs.id: obs for obs in observations}

    missing = [oid for oid in observation_ids if oid not in by_id]
    if missing:
        raise LookupError(f"Menu observation not found: {missing[0]}")

    # Preserve request order
    ordered = [by_id[oid] for oid in observation_ids]

    for obs in ordered:
        if obs.cabin_norm != cabin_key:
            raise ValueError(
                f"Observation {obs.id} has cabin '{obs.cabin_norm}', expected '{cabin_key}'"
            )

    columns: list[MenuCompareColumn] = []
    # observation_id -> (category, subcategory) -> list[MenuItem]
    grouped: dict[str, dict[tuple[str, str], list[MenuItem]]] = {}
    category_order: list[tuple[str, str]] = []
    seen_keys: set[tuple[str, str]] = set()

    for obs in ordered:
        capture = obs.capture
        if capture is None:
            raise LookupError(f"Menu capture missing for observation {obs.id}")

        filtered = sorted(
            [i for i in obs.items if _item_matches_type(i, type_key)],
            key=lambda i: (i.position or 1, i.title or ""),
        )
        available = _is_observation_available(obs, filtered)
        origin = capture.origin_iata or obs.origin_iata or ""
        dest = capture.dest_iata or obs.dest_iata or ""
        service = capture.service_date or obs.service_date
        assert service is not None
        oid = str(obs.id)

        columns.append(
            MenuCompareColumn(
                observation_id=oid,
                flight_number=capture.flight_number,
                origin_iata=origin,
                dest_iata=dest,
                service_date=service,
                cabin_norm=obs.cabin_norm,  # type: ignore[arg-type]
                cabin_marketing=obs.cabin_marketing,
                label=_flight_label(
                    flight_number=capture.flight_number,
                    origin_iata=origin,
                    dest_iata=dest,
                    service_date=service,
                ),
                available=available,
                item_count=len(filtered),
            )
        )

        by_cat: dict[tuple[str, str], list[MenuItem]] = defaultdict(list)
        for item in filtered:
            key = (item.category or "", item.subcategory or "")
            by_cat[key].append(item)
            if key not in seen_keys:
                seen_keys.add(key)
                category_order.append(key)
        grouped[oid] = by_cat

    summary_rows: list[MenuCompareSummaryRow] = []
    detail_rows: list[MenuCompareDetailRow] = []

    for category, subcategory in category_order:
        summary_values: dict[str, MenuMetricCounts] = {}
        detail_values: dict[str, list[MenuCompareItemDetail]] = {}
        for col in columns:
            items = grouped[col.observation_id].get((category, subcategory), [])
            summary_values[col.observation_id] = _metric_counts(items)
            detail_values[col.observation_id] = [_to_detail(i) for i in items]
        summary_rows.append(
            MenuCompareSummaryRow(
                category=category,
                subcategory=subcategory,
                values=summary_values,
            )
        )
        detail_rows.append(
            MenuCompareDetailRow(
                category=category,
                subcategory=subcategory,
                values=detail_values,
            )
        )

    return MenuCompareResponse(
        columns=columns,
        summary_rows=summary_rows,
        detail_rows=detail_rows,
        cabin=cabin_key,
        item_type=type_key,
    )
