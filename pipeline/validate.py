"""Field-level tolerant validation for LLM-normalized aircraft data."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError

from shared.schemas import (
    AircraftConfiguration,
    CabinConfiguration,
    DeckConfiguration,
    SeatCounts,
    SeatRatingSummary,
    WifiInfo,
)

_NESTED_MODELS: dict[str, type[BaseModel]] = {
    "seat_counts": SeatCounts,
    "wifi": WifiInfo,
    "seat_rating_summary": SeatRatingSummary,
}


def sanitize_empty_values(value: Any) -> Any:
    """Coerce AeroLOPA empty strings to None before Pydantic validation."""
    if value == "":
        return None
    if isinstance(value, dict):
        return {k: sanitize_empty_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_empty_values(v) for v in value]
    return value


def _validate_field(model: type[BaseModel], field_name: str, value: Any) -> Any:
    annotation = model.model_fields[field_name].annotation
    return TypeAdapter(annotation).validate_python(value)


def _validate_submodel(
    field_name: str,
    value: Any,
    base_value: Any,
    dropped_fields: list[str],
) -> dict[str, Any] | None:
    model_cls = _NESTED_MODELS[field_name]
    base_dict = base_value if isinstance(base_value, dict) else {}
    overlay = value if isinstance(value, dict) else {}

    try:
        return model_cls.model_validate({**base_dict, **overlay}).model_dump(mode="json")
    except ValidationError:
        pass

    merged = {**base_dict, **overlay}
    cleaned: dict[str, Any] = {}
    for sub_field, sub_value in merged.items():
        if sub_field not in model_cls.model_fields:
            continue
        try:
            cleaned[sub_field] = _validate_field(model_cls, sub_field, sub_value)
        except ValidationError:
            dropped_fields.append(f"{field_name}.{sub_field}")
            if sub_field in base_dict:
                cleaned[sub_field] = base_dict[sub_field]

    try:
        return model_cls.model_validate(cleaned).model_dump(mode="json")
    except ValidationError:
        dropped_fields.append(field_name)
        return base_dict if base_dict else None


def _validate_cabins(
    overlay: Any,
    base_cabins: dict[str, Any],
    dropped_fields: list[str],
) -> dict[str, Any]:
    if not isinstance(overlay, dict):
        return dict(base_cabins)

    result = dict(base_cabins)
    for cabin_key, cabin_overlay in overlay.items():
        if not isinstance(cabin_overlay, dict):
            dropped_fields.append(f"cabins.{cabin_key}")
            continue

        base_cabin = base_cabins.get(cabin_key) or {}
        merged_cabin = {**base_cabin, **cabin_overlay}
        cleaned: dict[str, Any] = {}

        for field_name, field_value in merged_cabin.items():
            if field_name not in CabinConfiguration.model_fields:
                continue
            try:
                cleaned[field_name] = _validate_field(CabinConfiguration, field_name, field_value)
            except ValidationError:
                dropped_fields.append(f"cabins.{cabin_key}.{field_name}")
                if field_name in base_cabin:
                    cleaned[field_name] = base_cabin[field_name]

        try:
            result[cabin_key] = CabinConfiguration.model_validate(cleaned).model_dump(mode="json")
        except ValidationError:
            dropped_fields.append(f"cabins.{cabin_key}")
            if cabin_key in base_cabins:
                result[cabin_key] = base_cabins[cabin_key]

    return result


def _validate_decks(
    overlay: Any,
    base_decks: dict[str, Any],
    dropped_fields: list[str],
) -> dict[str, Any]:
    if not isinstance(overlay, dict):
        return dict(base_decks)

    result = dict(base_decks)
    for deck_key, deck_overlay in overlay.items():
        if not isinstance(deck_overlay, dict):
            dropped_fields.append(f"decks.{deck_key}")
            continue

        base_deck = base_decks.get(deck_key) or {}
        merged_deck = {**base_deck, **deck_overlay}
        cleaned: dict[str, Any] = {}

        for field_name, field_value in merged_deck.items():
            if field_name not in DeckConfiguration.model_fields:
                continue
            if field_name == "cabins":
                cleaned["cabins"] = _validate_cabins(
                    field_value,
                    base_deck.get("cabins") or {},
                    dropped_fields,
                )
                continue
            if field_name in _NESTED_MODELS:
                validated = _validate_submodel(
                    field_name,
                    field_value,
                    base_deck.get(field_name),
                    dropped_fields,
                )
                if validated is not None:
                    cleaned[field_name] = validated
                continue
            try:
                cleaned[field_name] = _validate_field(DeckConfiguration, field_name, field_value)
            except ValidationError:
                dropped_fields.append(f"decks.{deck_key}.{field_name}")
                if field_name in base_deck:
                    cleaned[field_name] = base_deck[field_name]

        try:
            result[deck_key] = DeckConfiguration.model_validate(cleaned).model_dump(mode="json")
        except ValidationError:
            dropped_fields.append(f"decks.{deck_key}")
            if deck_key in base_decks:
                result[deck_key] = base_decks[deck_key]

    return result


def tolerant_validate_aircraft(
    merged: dict[str, Any],
    base: dict[str, Any],
) -> tuple[AircraftConfiguration, list[str]]:
    """Validate merged dict field-by-field; invalid fields fall back to base or are dropped."""
    merged = sanitize_empty_values(merged)
    base = sanitize_empty_values(base)
    dropped_fields: list[str] = []
    cleaned: dict[str, Any] = dict(base)

    for field_name, value in merged.items():
        if field_name not in AircraftConfiguration.model_fields:
            continue

        if field_name == "cabins":
            cleaned["cabins"] = _validate_cabins(
                value,
                base.get("cabins") or {},
                dropped_fields,
            )
            continue

        if field_name == "decks":
            cleaned["decks"] = _validate_decks(
                value,
                base.get("decks") or {},
                dropped_fields,
            )
            continue

        if field_name in _NESTED_MODELS:
            validated = _validate_submodel(
                field_name,
                value,
                base.get(field_name),
                dropped_fields,
            )
            if validated is not None:
                cleaned[field_name] = validated
            continue

        try:
            cleaned[field_name] = _validate_field(
                AircraftConfiguration,
                field_name,
                sanitize_empty_values(value),
            )
        except ValidationError:
            dropped_fields.append(field_name)
            if field_name in base:
                cleaned[field_name] = base[field_name]

    return AircraftConfiguration.model_validate(cleaned), dropped_fields
