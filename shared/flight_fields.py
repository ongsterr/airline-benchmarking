"""Field metadata for cabin flight features (airline-level, not aircraft PATCH)."""

from __future__ import annotations

from typing import Any, Literal

FieldType = Literal["string", "int", "list"]

FLIGHT_FIELDS = [
    "check_in_priority",
    "cabin_bag_pieces",
    "cabin_bag_kg_per_piece",
    "cabin_bag_kg_total",
    "checked_bag_pieces",
    "checked_bag_kg_per_piece",
    "checked_bag_kg_total",
    "boarding_priority",
    "lounge_access",
    "amenity_kit",
    "amenity_kit_brand",
]

FIELD_TYPES: dict[str, FieldType] = {
    "check_in_priority": "string",
    "cabin_bag_pieces": "int",
    "cabin_bag_kg_per_piece": "int",
    "cabin_bag_kg_total": "int",
    "checked_bag_pieces": "int",
    "checked_bag_kg_per_piece": "int",
    "checked_bag_kg_total": "int",
    "boarding_priority": "string",
    "lounge_access": "string",
    "amenity_kit": "list",
    "amenity_kit_brand": "string",
}


def field_label(field_key: str) -> str:
    return field_key.replace("_", " ").title()


def format_flight_value(value: Any) -> Any:
    if value is None:
        return "—"
    if isinstance(value, list):
        if not value:
            return "—"
        return ", ".join(str(v).strip() for v in value)
    return value


def coerce_flight_field_value(field_key: str, value: Any) -> Any:
    if field_key not in FIELD_TYPES:
        raise ValueError(f"Unknown flight field: {field_key}")

    field_type = FIELD_TYPES[field_key]

    if value is None or value == "" or value == "—":
        return None

    if field_type == "string":
        return str(value)

    if field_type == "int":
        if isinstance(value, bool):
            raise ValueError(f"Invalid integer value for {field_key}: {value!r}")
        return int(value)

    if field_type == "list":
        if isinstance(value, list):
            items = [str(v).strip() for v in value if str(v).strip()]
            return items or None
        if isinstance(value, str):
            items = [part.strip() for part in value.split(",") if part.strip()]
            return items or None
        raise ValueError(f"Invalid list value for {field_key}: {value!r}")

    raise ValueError(f"Unsupported field type for {field_key}")
