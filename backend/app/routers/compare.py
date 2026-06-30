"""Aircraft comparison endpoint."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.entities import AircraftConfiguration, Airline
from backend.app.routers.aircraft import get_aircraft_detail
from shared.schemas import CompareRow


AIRCRAFT_FIELDS = [
  "aircraft_type_displayed",
  "aircraft_code_displayed",
  "configuration",
  "total_seats",
  "fleet_count",
  "manufacturer",
  "haul_type",
  "ife_provider",
  "ife_system_name",
  "wifi_provider",
  "wifi_system_name",
]

CABIN_FIELDS = [
  "num_seats",
  "rows",
  "layout",
  "seat_manufacturer",
  "pitch_inch",
  "width_inch",
  "recline_inch",
  "recline_deg",
  "has_flat_bed",
  "screen_size_inch",
  "power_v",
  "usb_a_count",
  "usb_c_count",
  "direct_aisle_access_pct",
  "wireless_charging",
  "bluetooth_connectivity",
]


def _format_value(value: Any) -> Any:
  if value is None:
    return "—"
  if isinstance(value, bool):
    return "Yes" if value else "No"
  return value


def compare_aircraft(
  db: Session,
  svg_ids: list[str],
  cabin: str | None = None,
) -> list[CompareRow]:
  configs = []
  for svg_id in svg_ids:
    detail = get_aircraft_detail(db, svg_id)
    if detail:
      configs.append(detail)

  if not configs:
    return []

  rows: list[CompareRow] = []

  for field in AIRCRAFT_FIELDS:
    rows.append(
      CompareRow(
        feature=field.replace("_", " ").title(),
        category="Aircraft",
        values={c.svg_id: _format_value(getattr(c, field, None)) for c in configs},
      )
    )

  cabin_key = (cabin or "business").lower().replace(" ", "_")
  for field in CABIN_FIELDS:
    rows.append(
      CompareRow(
        feature=field.replace("_", " ").title(),
        category=f"Cabin ({cabin_key.replace('_', ' ').title()})",
        values={
          c.svg_id: _format_value(
            getattr(c.cabins.get(cabin_key), field, None) if c.cabins.get(cabin_key) else None
          )
          for c in configs
        },
      )
    )

  return rows
