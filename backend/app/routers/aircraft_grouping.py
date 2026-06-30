"""Group dual-deck records into combined aircraft configurations."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from pipeline.config import BASE_URL
from backend.app.models.entities import AircraftConfiguration as AircraftEntity
from backend.app.models.entities import Airline
from backend.app.models.entities import CabinConfiguration as CabinEntity
from shared.schemas import (
    AircraftConfiguration as AircraftSchema,
    AircraftListItem,
    CabinConfiguration,
    DeckConfiguration,
    DeckName,
    SeatCounts,
    SeatRatingSummary,
    WifiInfo,
)


def config_group_id(ac: AircraftEntity) -> str:
    return ac.parent_svg_id or ac.svg_id


def merge_seat_counts(counts_list: list[dict | None]) -> SeatCounts:
    merged = {"first": 0, "business": 0, "premium_economy": 0, "economy": 0, "total": 0}
    for counts in counts_list:
        if not counts:
            continue
        for key in merged:
            merged[key] += counts.get(key, 0) or 0
    return SeatCounts(**merged)


def build_configuration_string(seat_counts: SeatCounts) -> str:
    parts: list[str] = []
    if seat_counts.first:
        parts.append(f"{seat_counts.first}F")
    if seat_counts.business:
        parts.append(f"{seat_counts.business}J")
    if seat_counts.premium_economy:
        parts.append(f"{seat_counts.premium_economy}W")
    if seat_counts.economy:
        parts.append(f"{seat_counts.economy}M")
    return " ".join(parts)


def _pick_primary(members: list[AircraftEntity]) -> AircraftEntity:
    return max(members, key=lambda ac: ac.last_updated or date.min)


def _cabins_from_entity(c: CabinEntity) -> CabinConfiguration:
    return CabinConfiguration(
        cabin_type=c.cabin_type or "",
        cabin_class=c.cabin_class or "",
        num_seats=c.num_seats or 0,
        rows=c.rows,
        row_start=c.row_start,
        row_end=c.row_end,
        layout=c.layout,
        seat_manufacturer=c.seat_manufacturer,
        pitch_inch=c.pitch_inch,
        width_inch=c.width_inch,
        recline_inch=c.recline_inch,
        recline_deg=c.recline_deg,
        has_flat_bed=c.has_flat_bed,
        bed_flat_length_inch=c.bed_flat_length_inch,
        screen_size_inch=c.screen_size_inch,
        screen_description=c.screen_description,
        ife_provider=c.ife_provider,
        ife_system_name=c.ife_system_name,
        ife=c.ife,
        wifi_provider=c.wifi_provider,
        wifi_system_name=c.wifi_system_name,
        wifi_description=c.wifi_description,
        power_v=c.power_v,
        power_description=c.power_description,
        usb_a_availability=c.usb_a_availability,
        usb_a_count=c.usb_a_count,
        usb_c_availability=c.usb_c_availability,
        usb_c_count=c.usb_c_count,
        usb_description=c.usb_description,
        bluetooth_connectivity=c.bluetooth_connectivity,
        wireless_charging=c.wireless_charging,
        privacy_doors=c.privacy_doors,
        personal_gasper_vent=c.personal_gasper_vent,
        adjustable_headrest=c.adjustable_headrest,
        adjustable_headrest_description=c.adjustable_headrest_description,
        adjustable_armrests=c.adjustable_armrests,
        adjustable_armrests_description=c.adjustable_armrests_description,
        direct_aisle_access_pct=c.direct_aisle_access_pct,
        seat_description=c.seat_description,
    )


def _decks_for_record(ac: AircraftEntity) -> dict[str, DeckConfiguration]:
    cabins = {c.cabin_key: _cabins_from_entity(c) for c in ac.cabins}
    decks: dict[str, DeckConfiguration] = {}

    if ac.decks:
        for deck_key, deck_data in ac.decks.items():
            if not isinstance(deck_data, dict):
                continue
            deck_cabins_raw = deck_data.get("cabins") or {}
            if isinstance(deck_cabins_raw, dict) and deck_cabins_raw:
                parsed_cabins = {
                    key: CabinConfiguration.model_validate(value)
                    for key, value in deck_cabins_raw.items()
                    if isinstance(value, dict)
                }
            else:
                parsed_cabins = cabins if ac.deck == deck_key else {}
            decks[deck_key] = DeckConfiguration(
                deck=deck_data.get("deck", deck_key),
                svg_id=deck_data.get("svg_id", ac.svg_id),
                seat_counts=SeatCounts(**deck_data["seat_counts"]) if deck_data.get("seat_counts") else None,
                seat_rating_summary=(
                    SeatRatingSummary(**deck_data["seat_rating_summary"])
                    if deck_data.get("seat_rating_summary")
                    else None
                ),
                cabins=parsed_cabins,
            )
    elif ac.deck:
        decks[ac.deck] = DeckConfiguration(
            deck=ac.deck,
            svg_id=ac.svg_id,
            seat_counts=SeatCounts(**ac.seat_counts) if ac.seat_counts else None,
            seat_rating_summary=(
                SeatRatingSummary(**ac.seat_rating_summary) if ac.seat_rating_summary else None
            ),
            cabins=cabins,
        )
    return decks


def _merge_flat_cabins(decks: dict[str, DeckConfiguration]) -> dict[str, CabinConfiguration]:
    best: dict[str, CabinConfiguration] = {}
    for deck in decks.values():
        for cabin_key, cabin in deck.cabins.items():
            existing = best.get(cabin_key)
            if existing is None or cabin.num_seats > existing.num_seats:
                best[cabin_key] = cabin
    return best


def _merge_seat_rating_summaries(
    summaries: list[SeatRatingSummary | None],
) -> SeatRatingSummary | None:
    rated = green = yellow = red = 0
    for summary in summaries:
        if summary is None:
            continue
        rated += summary.rated_seat_count
        green += summary.green_count
        yellow += summary.yellow_count
        red += summary.red_count
    if rated == 0:
        return None
    return SeatRatingSummary(
        rated_seat_count=rated,
        green_count=green,
        yellow_count=yellow,
        red_count=red,
    )


def merge_list_items(members: list[tuple[AircraftEntity, Airline]]) -> AircraftListItem:
    aircraft_members = [ac for ac, _ in members]
    group_id = config_group_id(aircraft_members[0])
    primary_ac = _pick_primary(aircraft_members)
    primary_al = next(al for ac, al in members if ac.id == primary_ac.id)
    is_dual_deck = len(members) > 1 or any(ac.is_dual_deck for ac in aircraft_members)

    merged_counts = merge_seat_counts([ac.seat_counts for ac in aircraft_members])
    total_seats = sum(ac.total_seats or 0 for ac in aircraft_members)
    last_updated = max((ac.last_updated for ac in aircraft_members if ac.last_updated), default=None)

    source_url = f"{BASE_URL}/{group_id}" if len(members) > 1 else primary_ac.source_url

    return AircraftListItem(
        svg_id=group_id,
        airline_slug=primary_al.slug,
        airline_name=primary_al.name,
        is_dual_deck=is_dual_deck,
        aircraft_type_displayed=primary_ac.aircraft_type_displayed,
        aircraft_code_displayed=primary_ac.aircraft_code_displayed,
        configuration=build_configuration_string(merged_counts),
        total_seats=total_seats or merged_counts.total or None,
        seat_counts=merged_counts,
        source_url=source_url,
        last_updated=last_updated,
    )


def merge_detail_records(members: list[AircraftEntity]) -> AircraftSchema:
    group_id = config_group_id(members[0])
    primary = _pick_primary(members)
    airline = primary.airline
    is_dual_deck = len(members) > 1 or any(ac.is_dual_deck for ac in members)

    merged_counts = merge_seat_counts([ac.seat_counts for ac in members])
    total_seats = sum(ac.total_seats or 0 for ac in members)

    decks: dict[DeckName, DeckConfiguration] = {}
    for ac in sorted(members, key=lambda row: row.deck or ""):
        for deck_key, deck_config in _decks_for_record(ac).items():
            decks[deck_key] = deck_config

    cabins = _merge_flat_cabins(decks)
    deck_ratings = [deck.seat_rating_summary for deck in decks.values()]
    seat_rating_summary = _merge_seat_rating_summaries(deck_ratings)
    if seat_rating_summary is None:
        seat_rating_summary = _merge_seat_rating_summaries(
            [
                SeatRatingSummary(**ac.seat_rating_summary) if ac.seat_rating_summary else None
                for ac in members
            ]
        )

    descriptions = [ac.description for ac in members if ac.description]
    description = descriptions[0] if descriptions else None

    return AircraftSchema(
        svg_id=group_id,
        airline_iata=airline.iata_code or airline.slug.upper(),
        airline_name=airline.name,
        iata_code=primary.iata_code,
        aircraft_type=primary.aircraft_type,
        aircraft_type_displayed=primary.aircraft_type_displayed,
        aircraft_code_displayed=primary.aircraft_code_displayed,
        manufacturer=primary.manufacturer,
        haul_type=primary.haul_type,
        lifecycle=primary.lifecycle,
        is_dual_deck=is_dual_deck,
        deck=None,
        parent_svg_id=None,
        deck_state=primary.deck_state if is_dual_deck else None,
        fleet_count=primary.fleet_count,
        last_updated=max((ac.last_updated for ac in members if ac.last_updated), default=None),
        configuration=build_configuration_string(merged_counts),
        description=description,
        total_seats=total_seats or merged_counts.total or None,
        seat_counts=merged_counts,
        ife_provider=primary.ife_provider,
        ife_system_name=primary.ife_system_name,
        ife_description=primary.ife_description,
        wifi_provider=primary.wifi_provider,
        wifi_system_name=primary.wifi_system_name,
        wifi=WifiInfo(**primary.wifi) if primary.wifi else None,
        seat_rating_summary=seat_rating_summary,
        decks=decks,
        cabins=cabins,
    )


def group_aircraft_rows(
    rows: list[tuple[AircraftEntity, Airline]],
) -> list[tuple[str, list[tuple[AircraftEntity, Airline]]]]:
    grouped: dict[str, list[tuple[AircraftEntity, Airline]]] = defaultdict(list)
    for ac, al in rows:
        grouped[config_group_id(ac)].append((ac, al))
    return sorted(grouped.items(), key=lambda item: (item[1][0][1].name, item[0]))
