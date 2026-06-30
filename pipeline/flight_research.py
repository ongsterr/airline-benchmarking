"""LLM web research for airline cabin flight features."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from pipeline.prompts.flight_features_research_prompt import build_flight_features_research_prompt
from shared.schemas import (
    AirlineFlightFeatures,
    CabinFlightFeatures,
    FlightPageType,
    FlightResearchSource,
    FlightSourceCandidate,
)

logger = logging.getLogger(__name__)

_CABIN_KEYS = frozenset({"first", "business", "premium_economy", "economy"})


@dataclass
class FlightResearchResult:
    features: AirlineFlightFeatures
    sources_by_cabin: dict[str, list[FlightSourceCandidate]] = field(default_factory=dict)
    grounding_candidates: list[FlightSourceCandidate] = field(default_factory=list)
    source: str = "empty"  # "llm" or "empty"
    llm_parsed: dict[str, Any] | None = None
    grounding_metadata: dict[str, Any] | None = None
    research_model: str | None = None
    researched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _normalize_cabin_entry(key: str, data: dict[str, Any]) -> CabinFlightFeatures | None:
    if not isinstance(data, dict):
        return None
    cabin_class = data.get("cabin_class") or key.replace("_", " ").title()
    payload = {**data, "cabin_class": cabin_class}
    payload.pop("sources", None)
    if "features" in payload and isinstance(payload["features"], dict):
        nested = payload.pop("features")
        for k, v in nested.items():
            norm_key = k.replace("-", "_")
            if norm_key not in payload or payload.get(norm_key) is None:
                payload[norm_key] = v
    try:
        return CabinFlightFeatures.model_validate(payload)
    except Exception as exc:
        logger.warning("Invalid cabin flight data for %s: %s", key, exc)
        return None


def _parse_llm_response(parsed: dict[str, Any]) -> AirlineFlightFeatures:
    cabins_raw = parsed.get("cabins", parsed)
    if not isinstance(cabins_raw, dict):
        return AirlineFlightFeatures()

    cabins: dict[str, CabinFlightFeatures] = {}
    for key, value in cabins_raw.items():
        cabin_key = key.lower().replace(" ", "_")
        if cabin_key not in _CABIN_KEYS:
            continue
        cabin = _normalize_cabin_entry(cabin_key, value if isinstance(value, dict) else {})
        if cabin:
            cabins[cabin_key] = cabin
    return AirlineFlightFeatures(cabins=cabins)


def _infer_page_type(url: str, title: str | None) -> FlightPageType:
    text = f"{url} {title or ''}".lower()
    if "baggage" in text or "bag" in text:
        return "baggage"
    if "lounge" in text:
        return "lounge"
    if "check-in" in text or "checkin" in text or "check_in" in text:
        return "check_in"
    if any(
        token in text
        for token in (
            "cabin",
            "first-class",
            "business-class",
            "premium-economy",
            "economy-class",
            "amenity",
        )
    ):
        return "cabin_product"
    return "general"


def _parse_research_sources(
    cabin_key: str,
    sources_raw: Any,
) -> list[FlightSourceCandidate]:
    if not isinstance(sources_raw, list):
        return []
    candidates: list[FlightSourceCandidate] = []
    for item in sources_raw:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        try:
            src = FlightResearchSource.model_validate(item)
        except Exception:
            continue
        candidates.append(
            FlightSourceCandidate(
                url=src.url,
                cabin_keys=[cabin_key],
                page_type=_infer_page_type(src.url, src.title),
                title=src.title or src.publisher,
                source_type="discovered",
            )
        )
    return candidates


def _extract_sources_by_cabin(parsed: dict[str, Any]) -> dict[str, list[FlightSourceCandidate]]:
    cabins_raw = parsed.get("cabins", parsed)
    if not isinstance(cabins_raw, dict):
        return {}

    by_cabin: dict[str, list[FlightSourceCandidate]] = {}
    for key, value in cabins_raw.items():
        cabin_key = key.lower().replace(" ", "_")
        if cabin_key not in _CABIN_KEYS or not isinstance(value, dict):
            continue
        sources = _parse_research_sources(cabin_key, value.get("sources"))
        if sources:
            by_cabin[cabin_key] = sources
    return by_cabin


def _grounding_chunks_to_candidates(
    grounding_metadata: dict[str, Any],
) -> list[FlightSourceCandidate]:
    chunks = grounding_metadata.get("grounding_chunks") or grounding_metadata.get("groundingChunks") or []
    candidates: list[FlightSourceCandidate] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        web = chunk.get("web") or chunk.get("retrievedContext") or {}
        if not isinstance(web, dict):
            continue
        url = web.get("uri") or web.get("url")
        if not url:
            continue
        title = web.get("title")
        candidates.append(
            FlightSourceCandidate(
                url=url,
                cabin_keys=[],
                page_type=_infer_page_type(url, title),
                title=title,
                source_type="discovered",
            )
        )
    return candidates


def merge_sources_for_upsert(
    sources_by_cabin: dict[str, list[FlightSourceCandidate]],
    grounding_candidates: list[FlightSourceCandidate],
) -> list[tuple[FlightSourceCandidate, int | None, datetime]]:
    """Deduplicate URLs; merge cabin_keys when the same URL appears for multiple cabins."""
    researched_at = datetime.now(timezone.utc)
    by_url: dict[str, FlightSourceCandidate] = {}

    for cabin_key, sources in sources_by_cabin.items():
        for candidate in sources:
            existing = by_url.get(candidate.url)
            if existing:
                merged_keys = list(dict.fromkeys([*existing.cabin_keys, cabin_key, *candidate.cabin_keys]))
                existing.cabin_keys = merged_keys
                if not existing.title and candidate.title:
                    existing.title = candidate.title
            else:
                merged = candidate.model_copy(deep=True)
                if cabin_key not in merged.cabin_keys:
                    merged.cabin_keys = [*merged.cabin_keys, cabin_key]
                by_url[candidate.url] = merged

    for candidate in grounding_candidates:
        if candidate.url in by_url:
            continue
        by_url[candidate.url] = candidate

    return [(c, None, researched_at) for c in by_url.values()]


def _strip_json_fences(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _extract_grounding_metadata(response: Any) -> dict[str, Any] | None:
    meta = getattr(response, "response_metadata", None) or {}
    grounding = meta.get("grounding_metadata") or meta.get("groundingMetadata")
    if isinstance(grounding, dict) and grounding:
        return grounding
    return None


def extract_grounding_queries(grounding_metadata: dict[str, Any] | None) -> list[str]:
    if not grounding_metadata:
        return []
    queries = grounding_metadata.get("web_search_queries") or grounding_metadata.get("webSearchQueries") or []
    return [q for q in queries if isinstance(q, str)]


def research_flight_features(
    airline_slug: str,
    airline_name: str,
    model: str | None = None,
) -> FlightResearchResult:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY not set; no flight features researched")
        return FlightResearchResult(features=AirlineFlightFeatures(), source="empty")

    model_name = model or os.getenv("LLM_MODEL", "gemini-2.5-pro")
    researched_at = datetime.now(timezone.utc)

    try:
        system_prompt, human_message = build_flight_features_research_prompt(
            airline_slug, airline_name
        )
        llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0)
        llm_with_search = llm.bind_tools([{"google_search": {}}])
        response = llm_with_search.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_message)]
        )
        content = response.content
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        content = _strip_json_fences(str(content))
        parsed = json.loads(content, strict=False)
        features = _parse_llm_response(parsed)
        sources_by_cabin = _extract_sources_by_cabin(parsed)
        grounding_metadata = _extract_grounding_metadata(response)
        grounding_candidates = (
            _grounding_chunks_to_candidates(grounding_metadata) if grounding_metadata else []
        )

        return FlightResearchResult(
            features=features,
            sources_by_cabin=sources_by_cabin,
            grounding_candidates=grounding_candidates,
            source="llm" if features.cabins else "empty",
            llm_parsed=parsed,
            grounding_metadata=grounding_metadata,
            research_model=model_name,
            researched_at=researched_at,
        )
    except Exception as exc:
        logger.warning("Flight feature LLM research failed: %s", exc)
        return FlightResearchResult(features=AirlineFlightFeatures(), source="empty")


def primary_source_url(sources: list[tuple[FlightSourceCandidate, int | None, datetime]]) -> str | None:
    if not sources:
        return None
    return sources[0][0].url
