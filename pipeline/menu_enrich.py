"""Bulk Gemini enrichment for Emirates menu items already loaded in the DB."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.entities import MenuItem, MenuObservation
from pipeline.menu_config import DEFAULT_MENU_LLM_MODEL, MENU_HUB_IATA
from pipeline.prompts.menu_enrichment_prompt import (
    MENU_ENRICHMENT_PROMPT_VERSION,
    MENU_ENRICHMENT_VERSION,
    build_menu_enrichment_prompt,
)

logger = logging.getLogger(__name__)

ENRICHMENT_BATCH_SIZE = 50
ITEM_TYPES = frozenset({"food", "beverage"})
BEVERAGE_TYPES = frozenset({"alcoholic", "non_alcoholic"})
CONFIDENCE_TRUE_THRESHOLD = 0.90


@dataclass
class MenuEnrichResult:
    candidates: int = 0
    enriched: int = 0
    skipped_invalid: int = 0
    batches: int = 0
    source: str = "skipped"  # skipped | enriched | fallback
    llm_batches: list[dict[str, Any]] = field(default_factory=list)
    enrichment_version: str = MENU_ENRICHMENT_VERSION


def localization_target(origin_iata: str | None, dest_iata: str | None) -> str | None:
    """Non-DXB endpoint used for cuisine localization."""
    hub = MENU_HUB_IATA.upper()
    origin = (origin_iata or "").upper()
    dest = (dest_iata or "").upper()
    if dest and dest != hub:
        return dest
    if origin and origin != hub:
        return origin
    return None


def _chunk(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _parse_confidence(value: Any) -> tuple[float | None, bool]:
    """Return (confidence, ok). ok=False when the value is present but invalid."""
    if value is None:
        return None, True
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None, False
    if confidence < 0.0 or confidence > 1.0:
        return None, False
    return confidence, True


def _gate_bool(flag: bool | None, confidence: float | None) -> bool:
    return bool(flag) and confidence is not None and confidence >= CONFIDENCE_TRUE_THRESHOLD


def validate_enrichment_row(
    raw: dict[str, Any],
    *,
    expected_hash: str,
    expected_code: str,
) -> dict[str, Any] | None:
    """Validate one LLM enrichment object; return normalized fields or None."""
    if not isinstance(raw, dict):
        return None
    item_hash = str(raw.get("item_hash") or "").strip()
    code = str(raw.get("code") or "").strip()
    if item_hash != expected_hash or code != expected_code:
        return None

    item_type = raw.get("item_type")
    if item_type not in ITEM_TYPES:
        return None

    beverage_type = raw.get("beverage_type")
    is_vegetarian = _as_bool(raw.get("is_vegetarian"))
    is_vegan = _as_bool(raw.get("is_vegan"))
    is_localized = _as_bool(raw.get("is_localized"))
    note = raw.get("localization_note")
    if note is not None and not isinstance(note, str):
        note = str(note)
    note = (note or "").strip() or None

    localization_confidence, loc_ok = _parse_confidence(raw.get("localization_confidence"))
    vegetarian_confidence, veg_ok = _parse_confidence(raw.get("vegetarian_confidence"))
    vegan_confidence, vegan_ok = _parse_confidence(raw.get("vegan_confidence"))
    if not (loc_ok and veg_ok and vegan_ok):
        return None

    if item_type == "beverage":
        if beverage_type not in BEVERAGE_TYPES:
            return None
        food_fields = (
            is_vegetarian,
            is_vegan,
            is_localized,
            localization_confidence,
            vegetarian_confidence,
            vegan_confidence,
            note,
        )
        if any(v is not None for v in food_fields):
            # Allow clearing extras by forcing nulls rather than rejecting lightly polluted rows
            is_vegetarian = None
            is_vegan = None
            is_localized = None
            localization_confidence = None
            vegetarian_confidence = None
            vegan_confidence = None
            note = None
    else:
        if beverage_type is not None:
            beverage_type = None
        if is_vegetarian is None or is_vegan is None or is_localized is None:
            return None
        if (
            localization_confidence is None
            or vegetarian_confidence is None
            or vegan_confidence is None
        ):
            return None
        is_vegetarian = _gate_bool(is_vegetarian, vegetarian_confidence)
        is_vegan = _gate_bool(is_vegan, vegan_confidence)
        is_localized = _gate_bool(is_localized, localization_confidence)
        if is_vegan:
            is_vegetarian = True
        if is_localized and not note:
            return None

    return {
        "item_type": item_type,
        "beverage_type": beverage_type,
        "is_vegetarian": is_vegetarian,
        "is_vegan": is_vegan,
        "is_localized": is_localized,
        "vegetarian_confidence": vegetarian_confidence,
        "vegan_confidence": vegan_confidence,
        "localization_confidence": localization_confidence,
        "localization_note": note,
    }


def apply_enrichment_to_rows(
    rows: list[MenuItem],
    llm_parsed: dict[str, Any] | None,
    *,
    enriched_at: datetime | None = None,
    enrichment_version: str = MENU_ENRICHMENT_VERSION,
) -> tuple[int, int]:
    """Apply validated enrichments onto ORM rows. Returns (enriched, skipped_invalid)."""
    items_raw = (llm_parsed or {}).get("items")
    if not isinstance(items_raw, list):
        return 0, len(rows)

    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in items_raw:
        if not isinstance(raw, dict):
            continue
        key = (str(raw.get("item_hash") or "").strip(), str(raw.get("code") or "").strip())
        if not key[0] or key in by_key:
            continue  # ignore duplicates / empty
        by_key[key] = raw

    ts = enriched_at or datetime.now(timezone.utc)
    enriched = 0
    skipped = 0
    for row in rows:
        key = (row.item_hash, row.code)
        raw = by_key.get(key)
        if raw is None:
            skipped += 1
            continue
        validated = validate_enrichment_row(
            raw, expected_hash=row.item_hash, expected_code=row.code
        )
        if not validated:
            skipped += 1
            continue
        row.item_type = validated["item_type"]
        row.beverage_type = validated["beverage_type"]
        row.is_vegetarian = validated["is_vegetarian"]
        row.is_vegan = validated["is_vegan"]
        row.is_localized = validated["is_localized"]
        row.vegetarian_confidence = validated["vegetarian_confidence"]
        row.vegan_confidence = validated["vegan_confidence"]
        row.localization_confidence = validated["localization_confidence"]
        row.localization_note = validated["localization_note"]
        row.enrichment_version = enrichment_version
        row.enriched_at = ts
        enriched += 1
    return enriched, skipped


def _invoke_enrichment_llm(
    items: list[dict[str, Any]],
    *,
    origin_iata: str,
    dest_iata: str,
    localization_target_iata: str | None,
    cabin_norm: str | None,
    model: str | None = None,
) -> dict[str, Any] | None:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.info("GOOGLE_API_KEY not set; skipping menu enrichment")
        return None

    model_name = model or os.getenv("MENU_LLM_MODEL", DEFAULT_MENU_LLM_MODEL)
    system_prompt, human_message = build_menu_enrichment_prompt(
        items,
        origin_iata=origin_iata,
        dest_iata=dest_iata,
        localization_target=localization_target_iata,
        cabin_norm=cabin_norm,
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
        raise ValueError("Enrichment LLM returned non-object JSON")
    return parsed


def enrich_observation_items(
    db: Session,
    observation: MenuObservation,
    *,
    model: str | None = None,
) -> MenuEnrichResult:
    """Enrich menu_items for one observation where enriched_at IS NULL."""
    rows = (
        db.query(MenuItem)
        .filter(
            MenuItem.observation_id == observation.id,
            MenuItem.enriched_at.is_(None),
        )
        .order_by(MenuItem.position.asc(), MenuItem.code.asc())
        .all()
    )
    result = MenuEnrichResult(candidates=len(rows))
    if not rows:
        result.source = "skipped"
        return result

    origin = observation.origin_iata or ""
    dest = observation.dest_iata or ""
    target = localization_target(origin, dest)
    model_name = model or os.getenv("MENU_LLM_MODEL", DEFAULT_MENU_LLM_MODEL)
    version = f"{MENU_ENRICHMENT_VERSION}+{MENU_ENRICHMENT_PROMPT_VERSION}+{model_name}"
    result.enrichment_version = version

    batches = _chunk(rows, ENRICHMENT_BATCH_SIZE)
    result.batches = len(batches)
    total_enriched = 0
    total_skipped = 0

    for batch in batches:
        payload = [
            {
                "item_hash": row.item_hash,
                "code": row.code,
                "category": row.category,
                "subcategory": row.subcategory,
                "title": row.title,
                "desc": row.desc,
            }
            for row in batch
        ]
        try:
            parsed = _invoke_enrichment_llm(
                payload,
                origin_iata=origin,
                dest_iata=dest,
                localization_target_iata=target,
                cabin_norm=observation.cabin_norm,
                model=model_name,
            )
            if parsed is None:
                total_skipped += len(batch)
                continue
            result.llm_batches.append(parsed)
            enriched, skipped = apply_enrichment_to_rows(
                batch, parsed, enrichment_version=version
            )
            total_enriched += enriched
            total_skipped += skipped
        except Exception as exc:
            logger.warning(
                "Menu enrichment batch failed for observation=%s (%s)",
                observation.id,
                exc,
            )
            total_skipped += len(batch)

    result.enriched = total_enriched
    result.skipped_invalid = total_skipped
    if total_enriched > 0:
        result.source = "enriched"
        db.flush()
    else:
        result.source = "fallback"
    return result


__all__ = [
    "CONFIDENCE_TRUE_THRESHOLD",
    "ENRICHMENT_BATCH_SIZE",
    "MENU_ENRICHMENT_VERSION",
    "MenuEnrichResult",
    "apply_enrichment_to_rows",
    "enrich_observation_items",
    "localization_target",
    "validate_enrichment_row",
]
