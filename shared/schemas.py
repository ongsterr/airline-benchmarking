"""Pydantic models for aircraft hardware features (mirrors output.py)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

DeckName = Literal["main", "upper"]


class SeatCounts(BaseModel):
    first: int = 0
    business: int = 0
    premium_economy: int = 0
    economy: int = 0
    total: int = 0


class WifiInfo(BaseModel):
    technology: str | None = None
    tier: int | None = None
    rating: str | None = None
    cost: str | None = None
    fleet_pct: int | None = None


class SeatRatingSummary(BaseModel):
    rated_seat_count: int = 0
    green_count: int = 0
    yellow_count: int = 0
    red_count: int = 0


class CabinConfiguration(BaseModel):
    cabin_type: str
    cabin_class: str
    num_seats: int
    rows: str | None = None
    row_start: int | None = None
    row_end: int | None = None
    layout: str | None = None
    seat_manufacturer: str | None = None
    pitch_inch: float | None = None
    width_inch: float | None = None
    recline_inch: float | None = None
    recline_deg: float | None = None
    has_flat_bed: bool = False
    bed_flat_length_inch: float | None = None
    screen_size_inch: float | None = None
    screen_description: str | None = None
    ife_provider: str | None = None
    ife_system_name: str | None = None
    ife: str | None = None
    wifi_provider: str | None = None
    wifi_system_name: str | None = None
    wifi_description: str | None = None
    power_v: int | None = None
    power_description: str | None = None
    usb_a_availability: bool = False
    usb_a_count: int | None = None
    usb_c_availability: bool = False
    usb_c_count: int | None = None
    usb_description: str | None = None
    bluetooth_connectivity: str | None = None
    wireless_charging: str | None = None
    privacy_doors: str | None = None
    personal_gasper_vent: str | None = None
    adjustable_headrest: bool | None = None
    adjustable_headrest_description: str | None = None
    adjustable_armrests: bool | None = None
    adjustable_armrests_description: str | None = None
    direct_aisle_access_pct: int | None = None
    seat_description: str | None = None


class DeckConfiguration(BaseModel):
    deck: DeckName
    svg_id: str
    seat_counts: SeatCounts | None = None
    seat_rating_summary: SeatRatingSummary | None = None
    cabins: dict[str, CabinConfiguration] = Field(default_factory=dict)


class AircraftConfiguration(BaseModel):
    svg_id: str
    airline_iata: str
    airline_name: str
    iata_code: str | None = None
    aircraft_type: str | None = None
    aircraft_type_displayed: str | None = None
    aircraft_code_displayed: str | None = None
    manufacturer: str | None = None
    haul_type: str | None = None
    lifecycle: str | None = None
    is_dual_deck: bool = False
    deck: DeckName | None = None
    parent_svg_id: str | None = None
    deck_state: Literal["complete", "partial"] | None = None
    fleet_count: int | None = None
    last_updated: date | None = None
    configuration: str | None = None
    description: str | None = None
    total_seats: int | None = None
    seat_counts: SeatCounts | None = None
    ife_provider: str | None = None
    ife_system_name: str | None = None
    ife_description: str | None = None
    wifi_provider: str | None = None
    wifi_system_name: str | None = None
    wifi: WifiInfo | None = None
    seat_rating_summary: SeatRatingSummary | None = None
    decks: dict[DeckName, DeckConfiguration] = Field(default_factory=dict)
    cabins: dict[str, CabinConfiguration] = Field(default_factory=dict)


class AirlineSummary(BaseModel):
    slug: str
    iata_code: str | None = None
    name: str
    config_count: int = 0
    total_fleet_seats: int = 0
    aircraft_types: list[str] = Field(default_factory=list)
    last_pipeline_update: datetime | None = None


class AircraftListItem(BaseModel):
    svg_id: str
    airline_slug: str
    airline_name: str
    is_dual_deck: bool = False
    aircraft_type_displayed: str | None = None
    aircraft_code_displayed: str | None = None
    configuration: str | None = None
    total_seats: int | None = None
    seat_counts: SeatCounts | None = None
    source_url: str
    last_updated: date | None = None


class CompareRow(BaseModel):
    feature: str
    field_key: str
    scope: Literal["aircraft", "cabin"]
    category: str
    values: dict[str, Any]


class AircraftConfigUpdate(BaseModel):
    aircraft: dict[str, Any] = Field(default_factory=dict)
    cabins: dict[str, dict[str, Any]] = Field(default_factory=dict)


class CompareConfigColumn(BaseModel):
    svg_id: str
    airline_slug: str
    airline_name: str
    aircraft_type_displayed: str | None = None
    aircraft_code_displayed: str | None = None
    configuration: str | None = None
    source_url: str


class CompareResponse(BaseModel):
    columns: list[CompareConfigColumn]
    rows: list[CompareRow]
