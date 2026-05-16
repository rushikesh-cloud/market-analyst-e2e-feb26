from __future__ import annotations

import json
import re
from typing import Any, Iterable


RATING_MIN = 1
RATING_MAX = 100


def normalize_rating(value: object) -> int | None:
    """Normalize model/provider score output to the project rating contract."""

    number = _coerce_number(value)
    if number is None:
        return None
    return max(RATING_MIN, min(RATING_MAX, int(round(number))))


def extract_rating(payload: dict[str, Any], keys: Iterable[str] = ("rating", "score")) -> int | None:
    for key in keys:
        rating = normalize_rating(payload.get(key))
        if rating is not None:
            return rating
    return None


def extract_rating_from_text(
    text: str,
    *,
    keys: Iterable[str] = (
        "rating",
        "final_rating",
        "fundamental_rating",
        "technical_rating",
        "sentiment_score",
        "technical_score",
        "fundamental_score",
        "score",
    ),
) -> int | None:
    payload = parse_json_object(text)
    rating = extract_rating(payload, keys=keys)
    if rating is not None:
        return rating

    key_pattern = "|".join(re.escape(key).replace("_", r"[_\s-]?") for key in keys)
    match = re.search(rf"\b(?:{key_pattern})\b\D{{0,24}}(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if match:
        return normalize_rating(match.group(1))

    return None


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    return parsed if isinstance(parsed, dict) else {}


def _coerce_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"\d+(?:\.\d+)?", value)
        if match:
            return float(match.group(0))
    return None
