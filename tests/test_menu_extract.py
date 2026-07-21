"""Tests for Emirates menu cleaning, flatten, and blank-title LLM expansion."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

from pipeline.menu_extract import (
    EXTRACTOR_VERSION,
    apply_blank_title_expansions,
    clean_menu_text,
    extract_menu_from_api,
    map_api_payload_to_extraction,
)
from shared.schemas import MenuExtraction, MenuItem

SAMPLE_API = {
    "categories": [
        {
            "title": "Light Bites",
            "subCategories": [
                {
                    "title": "Snack",
                    "items": [
                        {
                            "code": "74971",
                            "title": "Margherita pizza<br/>",
                            "desc": "",
                        },
                        {
                            "code": "49312",
                            "title": "Chocolate&nbsp;coconut cake",
                            "desc": "With <b>cream</b>",
                        },
                    ],
                }
            ],
        },
        {
            "title": "Breakfast",
            "subCategories": [
                {
                    "title": "Appetiser",
                    "items": [
                        {
                            "code": "82673",
                            "title": "Fresh seasonal fruit",
                            "desc": "",
                        }
                    ],
                },
                {
                    "title": "Main Course",
                    "items": [
                        {
                            "code": "76246",
                            "title": "Vegan crêpes",
                            "desc": "Filled with carrots and peppers",
                        }
                    ],
                },
                {
                    "title": "Bread",
                    "items": [
                        {
                            "code": "59293",
                            "title": "Croissant<br/>",
                            "desc": "Served with butter<br/>and preserve",
                        }
                    ],
                },
            ],
        },
        {
            "title": "Beverages",
            "subCategories": [
                {
                    "title": "Juices and Soft Drinks",
                    "items": [
                        {
                            "code": "BV000112",
                            "title": "",
                            "desc": (
                                "Orange, pineapple, apple, mango or tomato"
                                "&lt;br /&gt;Cola and diet cola"
                            ),
                        },
                        {
                            "code": "BV000064",
                            "title": "Vitality Boost\r<br />",
                            "desc": "Natural drinks\x07 with no added sugar",
                        },
                    ],
                }
            ],
        },
    ]
}

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_clean_menu_text_strips_br_tags_entities_and_controls() -> None:
    assert clean_menu_text("Croissant<br/>") == "Croissant"
    assert clean_menu_text("Served with butter<br/>and preserve") == (
        "Served with butter and preserve"
    )
    assert clean_menu_text("Chocolate&nbsp;coconut") == "Chocolate coconut"
    assert clean_menu_text("With <b>cream</b>") == "With cream"
    assert clean_menu_text("<p>Hello</p>") == "Hello"
    assert clean_menu_text("tomato&lt;br /&gt;Cola") == "tomato Cola"
    assert clean_menu_text("Vitality Boost\r<br />") == "Vitality Boost"
    assert clean_menu_text("Natural\x07 drinks") == "Natural drinks"
    assert clean_menu_text("Vegan crêpes") == "Vegan crêpes"
    assert clean_menu_text("Moet & Chandon") == "Moet & Chandon"
    assert clean_menu_text("   ") is None
    assert clean_menu_text(None) is None


def test_deterministic_mapping_mirrors_api_labels() -> None:
    extraction = map_api_payload_to_extraction(
        SAMPLE_API, cabin_norm="economy", service_date=date(2026, 8, 1)
    )
    assert len(extraction.items) == 7
    by_hash = {i.item_hash: i for i in extraction.items}

    pizza = by_hash["m:74971"]
    assert pizza.category == "Light Bites"
    assert pizza.subcategory == "Snack"
    assert pizza.code == "74971"
    assert pizza.title == "Margherita pizza"
    assert pizza.desc is None

    blank = by_hash["m:BV000112"]
    assert blank.title == ""
    assert blank.desc is not None
    assert "Cola" in blank.desc


def test_apply_blank_title_expansions_splits_and_suffixes() -> None:
    base = map_api_payload_to_extraction(
        SAMPLE_API, cabin_norm="economy", service_date=date(2026, 8, 1)
    )
    llm_parsed = {
        "expansions": {
            "BV000112": [
                {"title": "Orange juice", "desc": None},
                {"title": "Pineapple juice<br/>", "desc": "Fresh"},
                {"title": "Cola", "desc": None},
                {"title": "  ", "desc": "ignored"},
            ],
            "UNKNOWN": [{"title": "Should ignore", "desc": None}],
        }
    }
    merged, expanded = apply_blank_title_expansions(base, llm_parsed)
    assert expanded == 1

    codes = [i.code for i in merged.items]
    assert "BV000112_1" in codes
    assert "BV000112_2" in codes
    assert "BV000112_3" in codes
    assert "BV000112" not in codes  # replaced
    assert "74971" in codes  # titled items unchanged
    assert "BV000064" in codes

    juice = next(i for i in merged.items if i.code == "BV000112_1")
    assert juice.title == "Orange juice"
    assert juice.category == "Beverages"
    assert juice.subcategory == "Juices and Soft Drinks"
    assert juice.item_hash == "m:BV000112_1"

    pineapple = next(i for i in merged.items if i.code == "BV000112_2")
    assert pineapple.title == "Pineapple juice"
    assert pineapple.desc == "Fresh"

    # Order: Light Bites snacks, breakfast items, then expanded juices, then Vitality
    titles = [i.title for i in merged.items]
    assert titles.index("Margherita pizza") < titles.index("Orange juice")
    assert titles.index("Orange juice") < titles.index("Vitality Boost")


def test_apply_preserves_blank_when_group_invalid() -> None:
    base = map_api_payload_to_extraction(
        SAMPLE_API, cabin_norm="economy", service_date=date(2026, 8, 1)
    )
    llm_parsed = {
        "expansions": {
            "BV000112": [{"title": "", "desc": "no title"}],
        }
    }
    merged, expanded = apply_blank_title_expansions(base, llm_parsed)
    assert expanded == 0
    blank = next(i for i in merged.items if i.code == "BV000112")
    assert blank.title == ""


def test_extract_expands_with_mocked_llm() -> None:
    llm_response = {
        "expansions": {
            "BV000112": [
                {"title": "Orange juice", "desc": None},
                {"title": "Cola", "desc": None},
            ]
        }
    }
    with patch(
        "pipeline.menu_extract._invoke_blank_title_llm", return_value=llm_response
    ):
        result = extract_menu_from_api(
            SAMPLE_API, cabin_norm="economy", service_date=date(2026, 8, 1)
        )
    assert result.source == "api+llm"
    assert result.llm_parsed == llm_response
    assert result.extractor_version and "menu_blank_title_prompt_v1" in (
        result.extractor_version or ""
    )
    codes = {i.code for i in result.extraction.items}
    assert "BV000112_1" in codes and "BV000112_2" in codes
    assert "74971" in codes


def test_extract_falls_back_without_api_key() -> None:
    with patch("pipeline.menu_extract._invoke_blank_title_llm", return_value=None):
        result = extract_menu_from_api(
            SAMPLE_API, cabin_norm="economy", service_date=date(2026, 8, 1)
        )
    assert result.source == "api_llm_fallback"
    blank = next(i for i in result.extraction.items if i.code == "BV000112")
    assert blank.title == ""


def test_extract_falls_back_on_llm_error() -> None:
    with patch(
        "pipeline.menu_extract._invoke_blank_title_llm",
        side_effect=RuntimeError("boom"),
    ):
        result = extract_menu_from_api(
            SAMPLE_API, cabin_norm="economy", service_date=date(2026, 8, 1)
        )
    assert result.source == "api_llm_fallback"
    assert len(result.extraction.items) == 7


def test_no_blank_titles_skips_llm() -> None:
    payload = {
        "categories": [
            {
                "title": "Dinner",
                "subCategories": [
                    {
                        "title": "Main Course",
                        "items": [
                            {"code": "1", "title": "Steak", "desc": "With fries"},
                        ],
                    }
                ],
            }
        ]
    }
    with patch("pipeline.menu_extract._invoke_blank_title_llm") as invoke:
        result = extract_menu_from_api(
            payload, cabin_norm="economy", service_date=date(2026, 8, 1)
        )
    invoke.assert_not_called()
    assert result.source == "api"
    assert result.extractor_version == EXTRACTOR_VERSION


def test_menu_extract_module_does_not_eager_load_langchain() -> None:
    """Fresh interpreter: importing menu_extract must not load langchain_google_genai."""
    import subprocess
    import sys

    script = (
        "import sys\n"
        "import pipeline.menu_extract\n"
        "assert 'langchain_google_genai' not in sys.modules\n"
        "assert 'langchain_core' not in sys.modules\n"
        "print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_bootstrap_skips_create_all_when_tables_exist() -> None:
    from pipeline import run_menu

    with (
        patch("pipeline.run_menu.menu_tables_exist", return_value=True) as exists,
        patch("pipeline.run_menu.init_schema") as init,
        patch("pipeline.run_menu.ensure_menu_columns") as ensure,
        patch.object(run_menu.Base.metadata, "create_all") as create_all,
    ):
        run_menu._bootstrap_menu_schema()
    exists.assert_called_once()
    init.assert_called_once()
    ensure.assert_called_once()
    create_all.assert_not_called()


def test_duplicate_and_missing_codes() -> None:
    payload = {
        "categories": [
            {
                "title": "Dinner",
                "subCategories": [
                    {
                        "title": "Main Course",
                        "items": [
                            {"code": "100", "title": "A", "desc": ""},
                            {"code": "100", "title": "B", "desc": ""},
                            {"code": "", "title": "No Code Dish", "desc": "Side salad"},
                        ],
                    }
                ],
            }
        ]
    }
    extraction = map_api_payload_to_extraction(
        payload, cabin_norm="business", service_date=date(2026, 8, 1)
    )
    hashes = [i.item_hash for i in extraction.items]
    assert hashes[0] == "m:100"
    assert hashes[1] == "m:100_2"
    assert hashes[2].startswith("m:no_code_dish")


def test_empty_payload() -> None:
    result = extract_menu_from_api(
        {"categories": []}, cabin_norm="economy", service_date=date(2026, 8, 1)
    )
    assert result.source == "empty"
    assert result.extraction.items == []


def test_menu_item_schema_raw_fields() -> None:
    item = MenuItem(
        category="Breakfast",
        subcategory="Bread",
        code="59293",
        title="Croissant",
        desc="Served with butter",
        item_hash="m:59293",
    )
    extraction = MenuExtraction(cabin_norm="economy", items=[item])
    assert extraction.items[0].subcategory == "Bread"


def test_ek582_blank_title_expands_when_mocked() -> None:
    path = REPO_ROOT / "data" / "raw" / "menu" / "dxb_dac_582_2026-08-01_j.json"
    if not path.exists():
        path = REPO_ROOT / "evidence" / "emirates" / "dxb_dac_582_2026-08-01_j.json"
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    base = map_api_payload_to_extraction(
        payload, cabin_norm="business", service_date=date(2026, 8, 1)
    )
    blank = next((i for i in base.items if i.code == "BV000112"), None)
    if blank is None:
        return
    assert blank.title == ""
    titled_before = [i for i in base.items if i.title]
    llm_parsed = {
        "expansions": {
            "BV000112": [
                {"title": "Orange juice", "desc": None},
                {"title": "Cola", "desc": None},
                {"title": "Still water", "desc": None},
            ]
        }
    }
    with patch(
        "pipeline.menu_extract._invoke_blank_title_llm", return_value=llm_parsed
    ):
        result = extract_menu_from_api(
            payload, cabin_norm="business", service_date=date(2026, 8, 1)
        )
    assert result.source == "api+llm"
    titled_after = [i for i in result.extraction.items if i.code.startswith("BV000112_")]
    assert len(titled_after) == 3
    # Non-blank originals still present
    for item in titled_before:
        match = next(
            (
                x
                for x in result.extraction.items
                if x.code == item.code and x.title == item.title
            ),
            None,
        )
        assert match is not None
