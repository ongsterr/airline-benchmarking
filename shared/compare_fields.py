"""Field metadata for compare view and config updates."""

from __future__ import annotations

from typing import Any, Literal

FieldType = Literal["string", "int", "float", "bool"]

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

FIELD_TYPES: dict[str, FieldType] = {
    "aircraft_type_displayed": "string",
    "aircraft_code_displayed": "string",
    "configuration": "string",
    "total_seats": "int",
    "fleet_count": "int",
    "manufacturer": "string",
    "haul_type": "string",
    "ife_provider": "string",
    "ife_system_name": "string",
    "wifi_provider": "string",
    "wifi_system_name": "string",
    "num_seats": "int",
    "rows": "string",
    "layout": "string",
    "seat_manufacturer": "string",
    "pitch_inch": "float",
    "width_inch": "float",
    "recline_inch": "float",
    "recline_deg": "float",
    "has_flat_bed": "bool",
    "screen_size_inch": "float",
    "power_v": "int",
    "usb_a_count": "int",
    "usb_c_count": "int",
    "direct_aisle_access_pct": "int",
    "wireless_charging": "string",
    "bluetooth_connectivity": "string",
}


def format_compare_value(value: Any) -> Any:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return value


def field_label(field_key: str) -> str:
    return field_key.replace("_", " ").title()


def coerce_field_value(field_key: str, value: Any) -> Any:
    if field_key not in FIELD_TYPES:
        raise ValueError(f"Unknown field: {field_key}")

    field_type = FIELD_TYPES[field_key]

    if value is None or value == "":
        if field_type == "bool":
            return False
        return None

    if field_type == "string":
        return str(value)

    if field_type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ("yes", "true", "1"):
                return True
            if normalized in ("no", "false", "0"):
                return False
        raise ValueError(f"Invalid boolean value for {field_key}: {value!r}")

    if field_type == "int":
        if isinstance(value, bool):
            raise ValueError(f"Invalid integer value for {field_key}: {value!r}")
        return int(value)

    if field_type == "float":
        if isinstance(value, bool):
            raise ValueError(f"Invalid float value for {field_key}: {value!r}")
        return float(value)

    raise ValueError(f"Unsupported field type for {field_key}")
