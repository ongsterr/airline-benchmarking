"""Extract embedded Next.js aircraft JSON from AeroLOPA HTML."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_aircraft_codes_from_html(html: str, slug: str) -> list[str]:
    """Extract aircraft_code values from embedded RSC payloads."""
    pattern = re.compile(rf'\\"aircraft_code\\":\\"({re.escape(slug)}-[^\\"]+)\\"')
    return list(dict.fromkeys(pattern.findall(html)))


def _find_balanced_json(text: str, start: int) -> str | None:
    """Extract a balanced JSON object starting at the opening brace."""
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _try_parse_aircraft_blob(blob: str) -> dict[str, Any] | None:
    """Attempt to parse a JSON blob as an aircraft object."""
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict) and ("aircraft_code" in data or "svg_id" in data):
        return data
    if isinstance(data, dict) and "aircraft" in data and isinstance(data["aircraft"], dict):
        return data["aircraft"]
    return None


def _richness_score(aircraft: dict[str, Any]) -> int:
    """Score aircraft dict by data completeness (prefer richer cabin payloads)."""
    score = len(aircraft)
    cabins = aircraft.get("cabins")
    if isinstance(cabins, list):
        score += len(cabins) * 10
        for cabin in cabins:
            if isinstance(cabin, dict):
                score += len(cabin) * 5
    elif isinstance(cabins, dict):
        score += len(cabins) * 10
        for cabin in cabins.values():
            if isinstance(cabin, dict):
                score += len(cabin) * 5
    if aircraft.get("seats"):
        score += 20
    if aircraft.get("wifi"):
        score += 5
    return score


def extract_aircraft_json(html: str) -> dict[str, Any] | None:
    """Locate and parse the richest aircraft object from Next.js RSC payloads."""
    candidates: list[dict[str, Any]] = []
    markers = ['"aircraft_code":', '\\"aircraft_code\\":', '"svg_id":', '\\"svg_id\\":']

    for marker in markers:
        idx = 0
        while True:
            pos = html.find(marker, idx)
            if pos == -1:
                break
            brace = html.rfind("{", max(0, pos - 8000), pos)
            if brace != -1:
                blob = _find_balanced_json(html, brace)
                if blob:
                    unescaped = blob.replace('\\"', '"').replace("\\\\", "\\")
                    for candidate_blob in (unescaped, blob):
                        result = _try_parse_aircraft_blob(candidate_blob)
                        if result and result not in candidates:
                            candidates.append(result)
            idx = pos + len(marker)

    code_match = re.search(
        r'\{[^{}]*(?:"aircraft_code"|\\"aircraft_code\\")'
        r'[^{}]*(?:"cabins"|\\"cabins\\")[^{}]*\}',
        html,
        re.DOTALL,
    )
    if code_match:
        for candidate in (code_match.group(0), code_match.group(0).replace('\\"', '"')):
            result = _try_parse_aircraft_blob(candidate)
            if result and result not in candidates:
                candidates.append(result)

    if not candidates:
        return None

    return max(candidates, key=_richness_score)
