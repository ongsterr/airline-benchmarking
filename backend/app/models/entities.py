"""SQLAlchemy ORM models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.config import settings
from backend.app.db.session import Base

SCHEMA = settings.db_schema


class Airline(Base):
    __tablename__ = "airlines"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    iata_code: Mapped[str | None] = mapped_column(String(3))
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    aircraft: Mapped[list[AircraftConfiguration]] = relationship(back_populates="airline")
    flight_features: Mapped[list[AirlineCabinFlightFeature]] = relationship(
        back_populates="airline", cascade="all, delete-orphan"
    )
    flight_sources: Mapped[list[FlightFeatureSource]] = relationship(
        back_populates="airline", cascade="all, delete-orphan"
    )


class AircraftConfiguration(Base):
    __tablename__ = "aircraft_configurations"
    __table_args__ = (
        UniqueConstraint("svg_id", name="uq_aircraft_svg_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    svg_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    airline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.airlines.id"), nullable=False, index=True
    )
    source_url: Mapped[str] = mapped_column(String(200), nullable=False)
    iata_code: Mapped[str | None] = mapped_column(String(10))
    aircraft_type: Mapped[str | None] = mapped_column(String(100))
    aircraft_type_displayed: Mapped[str | None] = mapped_column(String(100))
    aircraft_code_displayed: Mapped[str | None] = mapped_column(String(20))
    manufacturer: Mapped[str | None] = mapped_column(String(50))
    haul_type: Mapped[str | None] = mapped_column(String(50))
    lifecycle: Mapped[str | None] = mapped_column(String(20))
    is_dual_deck: Mapped[bool] = mapped_column(Boolean, default=False)
    deck: Mapped[str | None] = mapped_column(String(10))
    parent_svg_id: Mapped[str | None] = mapped_column(String(50), index=True)
    deck_state: Mapped[str | None] = mapped_column(String(20))
    decks: Mapped[dict | None] = mapped_column(JSONB)
    fleet_count: Mapped[int | None] = mapped_column(Integer)
    last_updated: Mapped[date | None] = mapped_column(Date, index=True)
    configuration: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    total_seats: Mapped[int | None] = mapped_column(Integer)
    seat_counts: Mapped[dict | None] = mapped_column(JSONB)
    ife_provider: Mapped[str | None] = mapped_column(String(100))
    ife_system_name: Mapped[str | None] = mapped_column(String(100))
    ife_description: Mapped[str | None] = mapped_column(Text)
    wifi_provider: Mapped[str | None] = mapped_column(String(100))
    wifi_system_name: Mapped[str | None] = mapped_column(String(100))
    wifi: Mapped[dict | None] = mapped_column(JSONB)
    seat_rating_summary: Mapped[dict | None] = mapped_column(JSONB)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    airline: Mapped[Airline] = relationship(back_populates="aircraft")
    cabins: Mapped[list[CabinConfiguration]] = relationship(
        back_populates="aircraft", cascade="all, delete-orphan"
    )


class CabinConfiguration(Base):
    __tablename__ = "cabin_configurations"
    __table_args__ = (
        UniqueConstraint("aircraft_id", "deck", "cabin_key", name="uq_aircraft_deck_cabin"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    aircraft_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.aircraft_configurations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deck: Mapped[str | None] = mapped_column(String(10))
    cabin_key: Mapped[str] = mapped_column(String(30), nullable=False)
    cabin_type: Mapped[str | None] = mapped_column(String(5))
    cabin_class: Mapped[str | None] = mapped_column(String(30))
    num_seats: Mapped[int | None] = mapped_column(Integer)
    rows: Mapped[str | None] = mapped_column(String(30))
    row_start: Mapped[int | None] = mapped_column(Integer)
    row_end: Mapped[int | None] = mapped_column(Integer)
    layout: Mapped[str | None] = mapped_column(String(20))
    seat_manufacturer: Mapped[str | None] = mapped_column(String(50))
    pitch_inch: Mapped[float | None] = mapped_column(Float)
    width_inch: Mapped[float | None] = mapped_column(Float)
    recline_inch: Mapped[float | None] = mapped_column(Float)
    recline_deg: Mapped[float | None] = mapped_column(Float)
    has_flat_bed: Mapped[bool] = mapped_column(Boolean, default=False)
    bed_flat_length_inch: Mapped[float | None] = mapped_column(Float)
    screen_size_inch: Mapped[float | None] = mapped_column(Float)
    screen_description: Mapped[str | None] = mapped_column(Text)
    ife_provider: Mapped[str | None] = mapped_column(String(100))
    ife_system_name: Mapped[str | None] = mapped_column(String(100))
    ife: Mapped[str | None] = mapped_column(Text)
    wifi_provider: Mapped[str | None] = mapped_column(String(100))
    wifi_system_name: Mapped[str | None] = mapped_column(String(100))
    wifi_description: Mapped[str | None] = mapped_column(Text)
    power_v: Mapped[int | None] = mapped_column(Integer)
    power_description: Mapped[str | None] = mapped_column(String(100))
    usb_a_availability: Mapped[bool] = mapped_column(Boolean, default=False)
    usb_a_count: Mapped[int | None] = mapped_column(Integer)
    usb_c_availability: Mapped[bool] = mapped_column(Boolean, default=False)
    usb_c_count: Mapped[int | None] = mapped_column(Integer)
    usb_description: Mapped[str | None] = mapped_column(Text)
    bluetooth_connectivity: Mapped[str | None] = mapped_column(String(20))
    wireless_charging: Mapped[str | None] = mapped_column(String(20))
    privacy_doors: Mapped[str | None] = mapped_column(String(20))
    personal_gasper_vent: Mapped[str | None] = mapped_column(String(20))
    adjustable_headrest: Mapped[bool | None] = mapped_column(Boolean)
    adjustable_headrest_description: Mapped[str | None] = mapped_column(Text)
    adjustable_armrests: Mapped[bool | None] = mapped_column(Boolean)
    adjustable_armrests_description: Mapped[str | None] = mapped_column(Text)
    direct_aisle_access_pct: Mapped[int | None] = mapped_column(Integer)
    seat_description: Mapped[str | None] = mapped_column(Text)

    aircraft: Mapped[AircraftConfiguration] = relationship(back_populates="cabins")


class FlightFeatureSource(Base):
    __tablename__ = "flight_feature_sources"
    __table_args__ = (
        UniqueConstraint("airline_id", "url", name="uq_flight_source_url"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    airline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.airlines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="curated")
    page_type: Mapped[str | None] = mapped_column(String(30))
    cabin_keys: Mapped[list | None] = mapped_column(JSONB)
    title: Mapped[str | None] = mapped_column(String(200))
    http_status: Mapped[int | None] = mapped_column(Integer)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    airline: Mapped[Airline] = relationship(back_populates="flight_sources")


class AirlineCabinFlightFeature(Base):
    __tablename__ = "airline_cabin_flight_features"
    __table_args__ = (
        UniqueConstraint("airline_id", "cabin_key", name="uq_airline_cabin_flight"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    airline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.airlines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cabin_key: Mapped[str] = mapped_column(String(30), nullable=False)
    cabin_class: Mapped[str | None] = mapped_column(String(30))
    check_in_priority: Mapped[str | None] = mapped_column(String(20))
    cabin_bag_pieces: Mapped[int | None] = mapped_column(Integer)
    cabin_bag_kg_per_piece: Mapped[int | None] = mapped_column(Integer)
    cabin_bag_kg_total: Mapped[int | None] = mapped_column(Integer)
    checked_bag_pieces: Mapped[int | None] = mapped_column(Integer)
    checked_bag_kg_per_piece: Mapped[int | None] = mapped_column(Integer)
    checked_bag_kg_total: Mapped[int | None] = mapped_column(Integer)
    boarding_priority: Mapped[str | None] = mapped_column(String(20))
    lounge_access: Mapped[str | None] = mapped_column(String(20))
    amenity_kit: Mapped[list | None] = mapped_column(JSONB)
    amenity_kit_brand: Mapped[str | None] = mapped_column(String(100))
    extra_features: Mapped[dict | None] = mapped_column(JSONB)
    source_url: Mapped[str | None] = mapped_column(String(500))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    airline: Mapped[Airline] = relationship(back_populates="flight_features")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    pipeline_type: Mapped[str] = mapped_column(String(20), default="hardware")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    airlines: Mapped[list] = mapped_column(JSONB)
    configs_discovered: Mapped[int] = mapped_column(Integer, default=0)
    configs_updated: Mapped[int] = mapped_column(Integer, default=0)
    configs_skipped: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list | None] = mapped_column(JSONB)
