"""Tests for LLM flight feature research parsing."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from pipeline.flight_research import (
    _normalize_cabin_entry,
    _parse_llm_response,
    _parse_research_sources,
    extract_grounding_queries,
    merge_sources_for_upsert,
    research_flight_features,
)
from shared.schemas import FlightSourceCandidate


SAMPLE_LLM_JSON = {
    "business": {
        "cabin_class": "Business",
        "sources": [
            {
                "url": "https://www.emirates.com/baggage",
                "title": "Baggage",
                "publisher": "emirates.com",
            },
            {
                "url": "https://www.emirates.com/business",
                "title": "Business class",
                "publisher": "emirates.com",
            },
        ],
        "features": {
            "check-in_priority": "Yes",
            "cabin_bag_pieces": 2,
            "cabin_bag_kg_per_piece": 7,
            "cabin_bag_kg_total": 14,
            "checked_bag_pieces": 2,
            "checked_bag_kg_per_piece": 23,
            "checked_bag_kg_total": 50,
            "boarding_priority": "Yes",
            "lounge_access": "Yes",
            "amenity_kit": ["Toothbrush", "Eyemask"],
            "amenity_kit_brand": "Bulgari",
        },
    },
    "economy": {
        "cabin_class": "Economy",
        "sources": [
            {
                "url": "https://www.emirates.com/economy",
                "title": "Economy",
                "publisher": "emirates.com",
            }
        ],
        "features": {
            "check-in_priority": "No",
            "lounge_access": "No",
            "amenity_kit": None,
            "amenity_kit_brand": None,
        },
    },
    "not_a_cabin": {"cabin_class": "Ignore", "features": {}},
}


def test_parse_llm_response_nested_features() -> None:
    features = _parse_llm_response(SAMPLE_LLM_JSON)
    assert set(features.cabins.keys()) == {"business", "economy"}
    business = features.cabins["business"]
    assert business.check_in_priority == "Yes"
    assert business.checked_bag_pieces == 2
    assert business.amenity_kit == ["Toothbrush", "Eyemask"]
    assert business.amenity_kit_brand == "Bulgari"


def test_hyphen_key_normalized_to_underscore() -> None:
    cabin = _normalize_cabin_entry(
        "business",
        {
            "cabin_class": "Business",
            "features": {"check-in_priority": "Yes"},
        },
    )
    assert cabin is not None
    assert cabin.check_in_priority == "Yes"


def test_parse_research_sources_infers_page_type() -> None:
    sources = _parse_research_sources(
        "business",
        SAMPLE_LLM_JSON["business"]["sources"],
    )
    assert len(sources) == 2
    assert sources[0].page_type == "baggage"
    assert sources[0].cabin_keys == ["business"]


def test_merge_sources_deduplicates_urls_across_cabins() -> None:
    shared_url = "https://www.emirates.com/baggage"
    by_cabin = {
        "business": [
            FlightSourceCandidate(url=shared_url, cabin_keys=["business"], page_type="baggage")
        ],
        "first": [
            FlightSourceCandidate(url=shared_url, cabin_keys=["first"], page_type="baggage")
        ],
    }
    merged = merge_sources_for_upsert(by_cabin, [])
    assert len(merged) == 1
    candidate, http_status, _ = merged[0]
    assert http_status is None
    assert set(candidate.cabin_keys) == {"business", "first"}


def test_extract_grounding_queries() -> None:
    queries = extract_grounding_queries(
        {"web_search_queries": ["emirates business baggage", "emirates lounge"]}
    )
    assert queries == ["emirates business baggage", "emirates lounge"]


@patch("pipeline.flight_research.ChatGoogleGenerativeAI")
def test_research_flight_features_mock_llm(mock_llm_cls) -> None:
    mock_response = MagicMock()
    mock_response.content = json.dumps(SAMPLE_LLM_JSON)
    mock_response.response_metadata = {}

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.return_value = mock_response
    mock_llm_cls.return_value = mock_llm

    with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
        result = research_flight_features("ek", "Emirates")

    assert result.source == "llm"
    assert "business" in result.features.cabins
    assert len(result.sources_by_cabin["business"]) == 2
    mock_llm.bind_tools.assert_called_once_with([{"google_search": {}}])
