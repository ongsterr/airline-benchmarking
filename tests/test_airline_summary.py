"""Tests for airline summary haul/manufacturer counting."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from backend.app.routers.airlines import _count_config_groups


def _config(
    svg_id: str,
    *,
    manufacturer: str | None = None,
    haul_type: str | None = None,
    parent_svg_id: str | None = None,
    last_updated: date | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        svg_id=svg_id,
        manufacturer=manufacturer,
        haul_type=haul_type,
        parent_svg_id=parent_svg_id,
        last_updated=last_updated or date(2026, 6, 1),
    )


def test_count_config_groups_mixed_haul_and_manufacturer() -> None:
    configs = [
        _config("ek-359g", manufacturer="Airbus", haul_type="Long Haul"),
        _config("ek-738g", manufacturer="Boeing", haul_type="Short Haul"),
        _config(
            "ek-388",
            manufacturer="Airbus",
            haul_type="Long Haul",
            last_updated=date(2026, 6, 1),
        ),
        _config(
            "ek-388l",
            manufacturer="Boeing",
            haul_type="Short Haul",
            parent_svg_id="ek-388",
            last_updated=date(2025, 1, 1),
        ),
    ]

    long_haul, short_haul, airbus, boeing, other = _count_config_groups(configs)

    assert long_haul == 2
    assert short_haul == 1
    assert airbus == 2
    assert boeing == 1
    assert other == 0


def test_count_config_groups_dual_deck_deduped() -> None:
    configs = [
        _config(
            "ek-388",
            manufacturer="Airbus",
            haul_type="Long Haul",
            last_updated=date(2026, 6, 1),
        ),
        _config(
            "ek-388l",
            manufacturer="Embraer",
            haul_type="Short Haul",
            parent_svg_id="ek-388",
            last_updated=date(2025, 1, 1),
        ),
    ]

    long_haul, short_haul, airbus, boeing, other = _count_config_groups(configs)

    assert long_haul == 1
    assert short_haul == 0
    assert airbus == 1
    assert boeing == 0
    assert other == 0


def test_count_config_groups_unknown_haul_and_manufacturer() -> None:
    configs = [_config("nz-32n", manufacturer=None, haul_type=None)]

    long_haul, short_haul, airbus, boeing, other = _count_config_groups(configs)

    assert long_haul == 0
    assert short_haul == 0
    assert airbus == 0
    assert boeing == 0
    assert other == 1
