"""Deck detection helpers for dual-deck AeroLOPA aircraft pages."""

from __future__ import annotations

from typing import Any

from shared.schemas import DeckName

DECK_SUFFIX: dict[str, DeckName] = {
    "-m": "main",
    "-u": "upper",
}


def deck_from_svg_id(svg_id: str) -> DeckName | None:
    for suffix, deck in DECK_SUFFIX.items():
        if svg_id.endswith(suffix):
            return deck
    return None


def parent_svg_id_from_svg_id(svg_id: str) -> str | None:
    for suffix in DECK_SUFFIX:
        if svg_id.endswith(suffix):
            return svg_id[: -len(suffix)]
    return None


def is_deck_page(svg_id: str) -> bool:
    return deck_from_svg_id(svg_id) is not None


def is_dual_deck_parent(svg_id: str, raw: dict[str, Any]) -> bool:
    if is_deck_page(svg_id):
        return False
    return bool(raw.get("is_dual_deck"))
