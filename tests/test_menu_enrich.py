"""Tests for Emirates menu item enrichment."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pipeline.menu_enrich import (
    ENRICHMENT_BATCH_SIZE,
    apply_enrichment_to_rows,
    enrich_observation_items,
    localization_target,
    validate_enrichment_row,
)
from pipeline.menu_load import _base_fields_equal, _clear_enrichment
from pipeline.prompts.menu_enrichment_prompt import (
    build_items_markdown_table,
    build_menu_enrichment_prompt,
)


def test_localization_target_prefers_non_dxb_endpoint() -> None:
    assert localization_target("DXB", "DAC") == "DAC"
    assert localization_target("LHR", "DXB") == "LHR"
    assert localization_target("DXB", "DXB") is None
    assert localization_target(None, "DAC") == "DAC"


def test_markdown_table_includes_item_fields() -> None:
    table = build_items_markdown_table(
        [
            {
                "item_hash": "m:1",
                "code": "1",
                "category": "Breakfast",
                "subcategory": "Main Course",
                "title": "Vegan crêpes",
                "desc": "With peppers",
            }
        ]
    )
    assert "| item_hash | code |" in table
    assert "Vegan crêpes" in table
    system, human = build_menu_enrichment_prompt(
        [{"item_hash": "m:1", "code": "1", "category": "Breakfast", "subcategory": "Main Course", "title": "A", "desc": "B"}],
        origin_iata="DXB",
        dest_iata="DAC",
        localization_target="DAC",
        cabin_norm="economy",
    )
    assert "DXB" in human and "DAC" in human
    assert "item_type" in system
    assert "vegetarian_confidence" in system
    assert "vegan_confidence" in system
    assert "≥ 0.90" in system


def test_validate_beverage_and_food_applicability() -> None:
    bev = validate_enrichment_row(
        {
            "item_hash": "m:BV1",
            "code": "BV1",
            "item_type": "beverage",
            "beverage_type": "alcoholic",
            "is_vegetarian": True,  # ignored / cleared
            "is_vegan": False,
            "is_localized": True,
            "vegetarian_confidence": 0.9,
            "vegan_confidence": 0.5,
            "localization_confidence": 0.5,
            "localization_note": "x",
        },
        expected_hash="m:BV1",
        expected_code="BV1",
    )
    assert bev is not None
    assert bev["beverage_type"] == "alcoholic"
    assert bev["is_vegetarian"] is None
    assert bev["is_localized"] is None
    assert bev["vegetarian_confidence"] is None
    assert bev["vegan_confidence"] is None

    food = validate_enrichment_row(
        {
            "item_hash": "m:2",
            "code": "2",
            "item_type": "food",
            "beverage_type": None,
            "is_vegetarian": False,
            "is_vegan": True,  # forces vegetarian
            "is_localized": True,
            "vegetarian_confidence": 0.95,
            "vegan_confidence": 0.95,
            "localization_confidence": 0.9,
            "localization_note": "Bengali khichuri",
        },
        expected_hash="m:2",
        expected_code="2",
    )
    assert food is not None
    assert food["is_vegan"] is True
    assert food["is_vegetarian"] is True
    assert food["vegetarian_confidence"] == 0.95
    assert food["vegan_confidence"] == 0.95

    bad_conf = validate_enrichment_row(
        {
            "item_hash": "m:3",
            "code": "3",
            "item_type": "food",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_localized": False,
            "vegetarian_confidence": 0.9,
            "vegan_confidence": 0.9,
            "localization_confidence": 1.5,
            "localization_note": None,
        },
        expected_hash="m:3",
        expected_code="3",
    )
    assert bad_conf is None

    mismatch = validate_enrichment_row(
        {"item_hash": "m:x", "code": "y", "item_type": "food"},
        expected_hash="m:1",
        expected_code="1",
    )
    assert mismatch is None


def test_confidence_threshold_gates_booleans() -> None:
    below = validate_enrichment_row(
        {
            "item_hash": "m:10",
            "code": "10",
            "item_type": "food",
            "beverage_type": None,
            "is_vegetarian": True,
            "is_vegan": True,
            "is_localized": True,
            "vegetarian_confidence": 0.89,
            "vegan_confidence": 0.89,
            "localization_confidence": 0.89,
            "localization_note": "borderline cuisine cue",
        },
        expected_hash="m:10",
        expected_code="10",
    )
    assert below is not None
    assert below["is_vegetarian"] is False
    assert below["is_vegan"] is False
    assert below["is_localized"] is False
    assert below["vegetarian_confidence"] == 0.89
    assert below["vegan_confidence"] == 0.89
    assert below["localization_confidence"] == 0.89

    at_threshold = validate_enrichment_row(
        {
            "item_hash": "m:11",
            "code": "11",
            "item_type": "food",
            "beverage_type": None,
            "is_vegetarian": True,
            "is_vegan": False,
            "is_localized": True,
            "vegetarian_confidence": 0.90,
            "vegan_confidence": 0.40,
            "localization_confidence": 0.90,
            "localization_note": "clear regional dish",
        },
        expected_hash="m:11",
        expected_code="11",
    )
    assert at_threshold is not None
    assert at_threshold["is_vegetarian"] is True
    assert at_threshold["is_vegan"] is False
    assert at_threshold["is_localized"] is True

    missing_veg_conf = validate_enrichment_row(
        {
            "item_hash": "m:12",
            "code": "12",
            "item_type": "food",
            "is_vegetarian": True,
            "is_vegan": False,
            "is_localized": False,
            "vegetarian_confidence": None,
            "vegan_confidence": 0.9,
            "localization_confidence": 0.5,
            "localization_note": None,
        },
        expected_hash="m:12",
        expected_code="12",
    )
    assert missing_veg_conf is None


def test_apply_enrichment_partial_and_duplicates() -> None:
    rows = [
        SimpleNamespace(
            item_hash="m:1",
            code="1",
            item_type=None,
            beverage_type=None,
            is_vegetarian=None,
            is_vegan=None,
            is_localized=None,
            vegetarian_confidence=None,
            vegan_confidence=None,
            localization_confidence=None,
            localization_note=None,
            enrichment_version=None,
            enriched_at=None,
        ),
        SimpleNamespace(
            item_hash="m:2",
            code="2",
            item_type=None,
            beverage_type=None,
            is_vegetarian=None,
            is_vegan=None,
            is_localized=None,
            vegetarian_confidence=None,
            vegan_confidence=None,
            localization_confidence=None,
            localization_note=None,
            enrichment_version=None,
            enriched_at=None,
        ),
    ]
    llm = {
        "items": [
            {
                "item_hash": "m:1",
                "code": "1",
                "item_type": "beverage",
                "beverage_type": "non_alcoholic",
                "is_vegetarian": None,
                "is_vegan": None,
                "is_localized": None,
                "vegetarian_confidence": None,
                "vegan_confidence": None,
                "localization_confidence": None,
                "localization_note": None,
            },
            {
                "item_hash": "m:1",
                "code": "1",
                "item_type": "beverage",
                "beverage_type": "alcoholic",
            },
            {
                "item_hash": "m:999",
                "code": "999",
                "item_type": "food",
                "is_vegetarian": True,
                "is_vegan": False,
                "is_localized": False,
                "vegetarian_confidence": 0.95,
                "vegan_confidence": 0.2,
                "localization_confidence": 0.8,
                "localization_note": None,
            },
        ]
    }
    enriched, skipped = apply_enrichment_to_rows(rows, llm)  # type: ignore[arg-type]
    assert enriched == 1
    assert skipped == 1
    assert rows[0].item_type == "beverage"
    assert rows[0].beverage_type == "non_alcoholic"  # first wins
    assert rows[0].enriched_at is not None
    assert rows[1].enriched_at is None


def test_enrich_observation_batches_and_fallback() -> None:
    observation = SimpleNamespace(
        id="obs-1",
        origin_iata="DXB",
        dest_iata="DAC",
        cabin_norm="economy",
    )
    # Build > batch size unenriched rows to exercise chunking
    rows = []
    for i in range(ENRICHMENT_BATCH_SIZE + 2):
        rows.append(
            SimpleNamespace(
                item_hash=f"m:{i}",
                code=str(i),
                category="Breakfast",
                subcategory="Main Course",
                title=f"Dish {i}",
                desc="desc",
                position=i,
                item_type=None,
                beverage_type=None,
                is_vegetarian=None,
                is_vegan=None,
                is_localized=None,
                vegetarian_confidence=None,
                vegan_confidence=None,
                localization_confidence=None,
                localization_note=None,
                enrichment_version=None,
                enriched_at=None,
            )
        )

    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value.order_by.return_value.all.return_value = rows

    def fake_invoke(payload, **kwargs):
        return {
            "items": [
                {
                    "item_hash": p["item_hash"],
                    "code": p["code"],
                    "item_type": "food",
                    "beverage_type": None,
                    "is_vegetarian": False,
                    "is_vegan": False,
                    "is_localized": False,
                    "vegetarian_confidence": 0.7,
                    "vegan_confidence": 0.6,
                    "localization_confidence": 0.7,
                    "localization_note": "generic",
                }
                for p in payload
            ]
        }

    with patch("pipeline.menu_enrich._invoke_enrichment_llm", side_effect=fake_invoke):
        result = enrich_observation_items(db, observation)  # type: ignore[arg-type]
    assert result.batches == 2
    assert result.enriched == ENRICHMENT_BATCH_SIZE + 2
    assert result.source == "enriched"
    db.flush.assert_called()

    with patch("pipeline.menu_enrich._invoke_enrichment_llm", return_value=None):
        result2 = enrich_observation_items(db, observation)  # type: ignore[arg-type]
    assert result2.source == "fallback"
    assert result2.enriched == 0


def test_base_fields_equal_and_clear_enrichment() -> None:
    row = SimpleNamespace(
        category="Breakfast",
        subcategory="Main Course",
        code="1",
        title="A",
        desc="B",
        item_type="food",
        beverage_type=None,
        is_vegetarian=True,
        is_vegan=False,
        is_localized=False,
        vegetarian_confidence=0.95,
        vegan_confidence=0.4,
        localization_confidence=0.5,
        localization_note="n",
        enrichment_version="v",
        enriched_at=datetime.now(timezone.utc),
    )
    item = SimpleNamespace(
        category="Breakfast",
        subcategory="Main Course",
        code="1",
        title="A",
        desc="B",
    )
    assert _base_fields_equal(row, item)  # type: ignore[arg-type]
    item.title = "Changed"
    assert not _base_fields_equal(row, item)  # type: ignore[arg-type]
    _clear_enrichment(row)  # type: ignore[arg-type]
    assert row.item_type is None
    assert row.vegetarian_confidence is None
    assert row.vegan_confidence is None
    assert row.enriched_at is None


def test_sample_style_food_and_beverage_validation() -> None:
    # Vegan dish on LHR-like route — localized false
    vegan = validate_enrichment_row(
        {
            "item_hash": "m:76246",
            "code": "76246",
            "item_type": "food",
            "beverage_type": None,
            "is_vegetarian": True,
            "is_vegan": True,
            "is_localized": False,
            "vegetarian_confidence": 0.95,
            "vegan_confidence": 0.95,
            "localization_confidence": 0.88,
            "localization_note": "Western vegan dish not specific to LHR",
        },
        expected_hash="m:76246",
        expected_code="76246",
    )
    assert vegan and vegan["is_vegan"] is True
    assert vegan["is_localized"] is False

    # DAC-localized food
    dac = validate_enrichment_row(
        {
            "item_hash": "m:80857",
            "code": "80857",
            "item_type": "food",
            "beverage_type": None,
            "is_vegetarian": False,
            "is_vegan": False,
            "is_localized": True,
            "vegetarian_confidence": 0.98,
            "vegan_confidence": 0.98,
            "localization_confidence": 0.93,
            "localization_note": "Bengali-style mutton khichuri for DAC",
        },
        expected_hash="m:80857",
        expected_code="80857",
    )
    assert dac and dac["is_localized"] is True

    # Alcoholic cocktail
    cocktail = validate_enrichment_row(
        {
            "item_hash": "m:BV000037",
            "code": "BV000037",
            "item_type": "beverage",
            "beverage_type": "alcoholic",
            "is_vegetarian": None,
            "is_vegan": None,
            "is_localized": None,
            "vegetarian_confidence": None,
            "vegan_confidence": None,
            "localization_confidence": None,
            "localization_note": None,
        },
        expected_hash="m:BV000037",
        expected_code="BV000037",
    )
    assert cocktail and cocktail["beverage_type"] == "alcoholic"
