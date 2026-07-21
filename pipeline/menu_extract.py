"""Extract Emirates digital-menu API JSON into MenuExtraction.

Flow: deterministic clean/flatten → optional blank-title Gemini expansion.
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from bs4 import BeautifulSoup

from pipeline.menu_config import DEFAULT_MENU_LLM_MODEL, MENU_CABIN_MARKETING
from pipeline.prompts.menu_blank_title_prompt import (
    MENU_BLANK_TITLE_PROMPT_VERSION,
    build_menu_blank_title_expansion_prompt,
)
from shared.schemas import MenuExtraction, MenuItem

logger = logging.getLogger(__name__)

EXTRACTOR_VERSION = "menu_api_transform_v2"

# Control chars except tab (converted to space via whitespace collapse)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass
class MenuExtractResult:
    extraction: MenuExtraction
    source: str  # "api" | "api+llm" | "api_llm_fallback" | "empty"
    extractor_version: str | None = None
    llm_parsed: dict[str, Any] | None = None
    blank_title_candidates: list[dict[str, Any]] = field(default_factory=list)


def _empty_extraction(cabin_norm: str) -> MenuExtraction:
    return MenuExtraction(
        cabin_norm=cabin_norm,  # type: ignore[arg-type]
        cabin_marketing=MENU_CABIN_MARKETING.get(cabin_norm),
        menu_cycle=None,
        grain_observed=[],
        confidence_tier=3,
        items=[],
    )


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return re.sub(r"_+", "_", slug)[:60] or "item"


def clean_menu_text(value: Any) -> str | None:
    """Strip HTML fragments, decode entities, remove control/line breaks, normalize whitespace.

    Preserves punctuation and Unicode accents. Returns None for empty results.
    """
    if value is None:
        return None
    raw = str(value)
    if not raw.strip():
        return None

    # Decode entities first so encoded tags like &lt;br /&gt; become real tags
    raw = html.unescape(raw)
    # Second pass for double-encoded fragments (&amp;lt;br&amp;gt;)
    if "&lt;" in raw or "&gt;" in raw or "&amp;" in raw or "&nbsp;" in raw.lower():
        raw = html.unescape(raw)

    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?i)</p\s*>", "\n", raw)
    raw = re.sub(r"(?i)</div\s*>", "\n", raw)

    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(" ", strip=False)
    text = html.unescape(text)
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")
    text = _CONTROL_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = re.sub(r"<[^>]+>", "", text).strip()
    return text or None


def _allocate_hash(seen_hashes: set[str], item_hash: str) -> str:
    base = item_hash
    n = 2
    while item_hash in seen_hashes:
        item_hash = f"{base}_{n}"
        n += 1
    seen_hashes.add(item_hash)
    return item_hash


def map_api_payload_to_extraction(
    payload: dict[str, Any],
    *,
    cabin_norm: str,
    service_date: date,
) -> MenuExtraction:
    """Deterministic flatten of Emirates digital-menu JSON → MenuExtraction."""
    items: list[MenuItem] = []
    seen_hashes: set[str] = set()
    position = 0

    for category in payload.get("categories") or []:
        if not isinstance(category, dict):
            continue
        cat_title = clean_menu_text(category.get("title")) or ""
        for subcategory in category.get("subCategories") or []:
            if not isinstance(subcategory, dict):
                continue
            sub_title = clean_menu_text(subcategory.get("title")) or ""
            for raw_item in subcategory.get("items") or []:
                if not isinstance(raw_item, dict):
                    continue
                code = clean_menu_text(raw_item.get("code")) or ""
                title = clean_menu_text(raw_item.get("title")) or ""
                desc = clean_menu_text(raw_item.get("desc"))

                # Keep blank-title items when code or desc is present
                if not code and not title and not desc:
                    continue

                item_hash = f"m:{code}" if code else f"m:{_slugify(title or desc or 'item')}"
                item_hash = _allocate_hash(seen_hashes, item_hash)

                position += 1
                items.append(
                    MenuItem(
                        category=cat_title,
                        subcategory=sub_title,
                        code=code,
                        title=title,
                        desc=desc,
                        position=position,
                        item_hash=item_hash,
                    )
                )

    return MenuExtraction(
        cabin_norm=cabin_norm,  # type: ignore[arg-type]
        cabin_marketing=MENU_CABIN_MARKETING.get(cabin_norm),
        menu_cycle=service_date.strftime("%Y-%m"),
        grain_observed=["airline", "cabin", "route", "direction", "date"],
        confidence_tier=1 if items else 3,
        items=items,
    )


def _blank_title_candidates(items: list[MenuItem]) -> list[dict[str, Any]]:
    """Items with empty title and non-empty desc, keyed for the LLM by base code."""
    candidates: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for item in items:
        if item.title or not item.desc:
            continue
        base_code = item.code or item.item_hash.removeprefix("m:")
        if not base_code or base_code in seen_codes:
            continue
        seen_codes.add(base_code)
        candidates.append(
            {
                "base_code": base_code,
                "category": item.category,
                "subcategory": item.subcategory,
                "desc": item.desc,
            }
        )
    return candidates


def _invoke_blank_title_llm(
    candidates: list[dict[str, Any]],
    *,
    cabin_norm: str,
    model: str | None = None,
) -> dict[str, Any] | None:
    # Lazy import: avoid loading LangChain/Gemini unless blank-title expansion runs
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.info("GOOGLE_API_KEY not set; skipping blank-title expansion")
        return None

    model_name = model or os.getenv("MENU_LLM_MODEL", DEFAULT_MENU_LLM_MODEL)
    cabin_marketing = MENU_CABIN_MARKETING.get(cabin_norm)
    system_prompt, human_message = build_menu_blank_title_expansion_prompt(
        candidates,
        cabin_norm=cabin_norm,
        cabin_marketing=cabin_marketing,
    )
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0,
    )
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_message),
        ]
    )
    content = response.content
    if isinstance(content, list):
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    content = str(content).strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
    parsed = json.loads(content, strict=False)
    if not isinstance(parsed, dict):
        raise ValueError("LLM returned non-object JSON")
    return parsed


def _parse_expansion_rows(
    raw_rows: Any,
) -> list[tuple[str, str | None]] | None:
    """Return cleaned (title, desc) pairs, or None if the group is invalid."""
    if not isinstance(raw_rows, list) or not raw_rows:
        return None
    parsed: list[tuple[str, str | None]] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        title = clean_menu_text(row.get("title"))
        if not title:
            continue
        desc = clean_menu_text(row.get("desc"))
        parsed.append((title, desc))
    return parsed or None


def apply_blank_title_expansions(
    extraction: MenuExtraction,
    llm_parsed: dict[str, Any] | None,
) -> tuple[MenuExtraction, int]:
    """Replace blank-title items with LLM-split rows where valid.

    Returns (merged extraction, number of blank candidates successfully expanded).
    """
    expansions_raw = (llm_parsed or {}).get("expansions")
    expansions: dict[str, list[tuple[str, str | None]]] = {}
    if isinstance(expansions_raw, dict):
        for key, value in expansions_raw.items():
            if not isinstance(key, str) or key in expansions:
                continue  # ignore duplicates / non-string keys
            rows = _parse_expansion_rows(value)
            if rows:
                expansions[key] = rows

    seen_hashes: set[str] = set()
    merged: list[MenuItem] = []
    expanded_count = 0
    position = 0

    for item in extraction.items:
        is_blank = not item.title and bool(item.desc)
        base_code = item.code or item.item_hash.removeprefix("m:")
        rows = expansions.get(base_code) if is_blank else None

        if rows:
            expanded_count += 1
            for idx, (title, desc) in enumerate(rows, start=1):
                if item.code:
                    code = f"{item.code}_{idx}"
                elif base_code:
                    code = f"{base_code}_{idx}"
                else:
                    code = f"{_slugify(title)}_{idx}"
                item_hash = _allocate_hash(seen_hashes, f"m:{code}")
                position += 1
                merged.append(
                    MenuItem(
                        category=item.category,
                        subcategory=item.subcategory,
                        code=code,
                        title=title,
                        desc=desc,
                        position=position,
                        item_hash=item_hash,
                    )
                )
            continue

        # Preserve original (titled items, or blank items that failed expansion)
        item_hash = _allocate_hash(seen_hashes, item.item_hash)
        position += 1
        merged.append(
            item.model_copy(update={"position": position, "item_hash": item_hash})
        )

    return extraction.model_copy(update={"items": merged}), expanded_count


def extract_menu_from_api(
    payload: dict[str, Any] | None,
    *,
    cabin_norm: str,
    service_date: date,
    model: str | None = None,
) -> MenuExtractResult:
    if not payload:
        return MenuExtractResult(
            extraction=_empty_extraction(cabin_norm),
            source="empty",
            extractor_version=EXTRACTOR_VERSION,
        )

    extraction = map_api_payload_to_extraction(
        payload, cabin_norm=cabin_norm, service_date=service_date
    )
    if not extraction.items:
        logger.info("API payload had no items for cabin=%s", cabin_norm)
        return MenuExtractResult(
            extraction=extraction,
            source="empty",
            extractor_version=EXTRACTOR_VERSION,
        )

    candidates = _blank_title_candidates(extraction.items)
    if not candidates:
        return MenuExtractResult(
            extraction=extraction,
            source="api",
            extractor_version=EXTRACTOR_VERSION,
            blank_title_candidates=[],
        )

    model_name = model or os.getenv("MENU_LLM_MODEL", DEFAULT_MENU_LLM_MODEL)
    version_base = f"{EXTRACTOR_VERSION}+{MENU_BLANK_TITLE_PROMPT_VERSION}"

    try:
        parsed = _invoke_blank_title_llm(
            candidates, cabin_norm=cabin_norm, model=model_name
        )
        if parsed is None:
            return MenuExtractResult(
                extraction=extraction,
                source="api_llm_fallback",
                extractor_version=f"{version_base}+deterministic",
                blank_title_candidates=candidates,
            )

        merged, expanded_count = apply_blank_title_expansions(extraction, parsed)
        if expanded_count == 0:
            return MenuExtractResult(
                extraction=extraction,
                source="api_llm_fallback",
                extractor_version=f"{version_base}+{model_name}",
                llm_parsed=parsed,
                blank_title_candidates=candidates,
            )

        return MenuExtractResult(
            extraction=merged,
            source="api+llm",
            extractor_version=f"{version_base}+{model_name}",
            llm_parsed=parsed,
            blank_title_candidates=candidates,
        )
    except Exception as exc:
        logger.warning(
            "Blank-title LLM expansion failed for cabin=%s (%s); keeping deterministic rows",
            cabin_norm,
            exc,
        )
        return MenuExtractResult(
            extraction=extraction,
            source="api_llm_fallback",
            extractor_version=f"{version_base}+deterministic",
            blank_title_candidates=candidates,
        )


__all__ = [
    "EXTRACTOR_VERSION",
    "MenuExtractResult",
    "apply_blank_title_expansions",
    "clean_menu_text",
    "extract_menu_from_api",
    "map_api_payload_to_extraction",
]
