"""Generate EPD-style typed JSON output skeleton from Pydantic schemas."""

from __future__ import annotations

import types
from datetime import date
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel

from shared.schemas import (
    AircraftConfiguration,
    CabinConfiguration,
    DeckConfiguration,
    SeatCounts,
    SeatRatingSummary,
    WifiInfo,
)

_CABIN_KEYS = ("first", "business", "premium_economy", "economy")
_DECK_KEYS = ("main", "upper")


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        args = get_args(annotation)
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1:
            return non_none[0], True
    return annotation, False


def _type_token(annotation: Any) -> str:
    annotation, nullable = _unwrap_optional(annotation)

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        token = _format_model_inline(annotation)
    elif annotation is str:
        token = "<string>"
    elif annotation is int:
        token = "<integer>"
    elif annotation is float:
        token = "<float>"
    elif annotation is bool:
        token = "<boolean>"
    elif annotation is date:
        token = "<string YYYY-MM-DD>"
    elif annotation is Any:
        token = "<any>"
    else:
        origin = get_origin(annotation)
        if origin is dict:
            token = "<object>"
        else:
            token = "<unknown>"

    if nullable:
        return f"{token}|null"
    return token


def _format_model_inline(model: type[BaseModel], indent: int = 0) -> str:
    pad = "    " * indent
    inner_pad = "    " * (indent + 1)
    lines = ["{"]
    fields = list(model.model_fields.items())
    for index, (name, field) in enumerate(fields):
        comma = "," if index < len(fields) - 1 else ""
        type_str = _type_token(field.annotation)
        if isinstance(field.annotation, type) and issubclass(
            _unwrap_optional(field.annotation)[0], BaseModel
        ):
            nested = _format_model_inline(_unwrap_optional(field.annotation)[0], indent + 1)
            lines.append(f'{inner_pad}"{name}": {nested}{comma}')
        else:
            lines.append(f'{inner_pad}"{name}": {type_str}{comma}')
    lines.append(f"{pad}}}")
    return "\n".join(lines)


def _format_cabins(indent: int = 1) -> str:
    pad = "    " * indent
    inner_pad = "    " * (indent + 1)
    cabin_skeleton = _format_model_inline(CabinConfiguration, indent + 2)
    lines = ["{"]
    for index, key in enumerate(_CABIN_KEYS):
        comma = "," if index < len(_CABIN_KEYS) - 1 else ""
        lines.append(f'{inner_pad}"{key}": {cabin_skeleton}{comma}')
    lines.append(f"{pad}}}")
    return "\n".join(lines)


def _format_decks(indent: int = 1) -> str:
    pad = "    " * indent
    inner_pad = "    " * (indent + 1)
    deck_skeleton = _format_model_inline(DeckConfiguration, indent + 2)
    lines = ["{"]
    for index, key in enumerate(_DECK_KEYS):
        comma = "," if index < len(_DECK_KEYS) - 1 else ""
        lines.append(f'{inner_pad}"{key}": {deck_skeleton}{comma}')
    lines.append(f"{pad}}}")
    return "\n".join(lines)


def build_output_format() -> str:
    """Return EPD-style output_format section for the aircraft hardware prompt."""
    pad = "    "
    lines = [
        "Return the output in JSON format in this exact structure without any other text or comments:",
        "{",
    ]

    fields = list(AircraftConfiguration.model_fields.items())
    for index, (name, field) in enumerate(fields):
        comma = "," if index < len(fields) - 1 else ""
        inner_type, nullable = _unwrap_optional(field.annotation)

        if name == "cabins":
            cabins_block = _format_cabins(indent=1)
            lines.append(f'{pad}"{name}": {cabins_block}{comma}')
        elif name == "decks":
            decks_block = _format_decks(indent=1)
            lines.append(f'{pad}"{name}": {decks_block}{comma}')
        elif inner_type is SeatCounts:
            nested = _format_model_inline(SeatCounts, indent=1)
            note = "  // or null" if nullable else ""
            lines.append(f'{pad}"{name}": {nested}{comma}{note}')
        elif inner_type is WifiInfo:
            nested = _format_model_inline(WifiInfo, indent=1)
            note = "  // or null" if nullable else ""
            lines.append(f'{pad}"{name}": {nested}{comma}{note}  // object, NOT a list')
        elif inner_type is SeatRatingSummary:
            nested = _format_model_inline(SeatRatingSummary, indent=1)
            note = "  // or null" if nullable else ""
            lines.append(f'{pad}"{name}": {nested}{comma}{note}')
        elif isinstance(inner_type, type) and issubclass(inner_type, BaseModel):
            nested = _format_model_inline(inner_type, indent=1)
            note = "  // or null" if nullable else ""
            lines.append(f'{pad}"{name}": {nested}{comma}{note}')
        else:
            token = _type_token(field.annotation)
            lines.append(f'{pad}"{name}": {token}{comma}')

    lines.append("}")
    return "\n".join(lines)
