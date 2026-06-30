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
