from __future__ import annotations

import re
from typing import Any

from market_analyst.services.scoring import extract_rating
from market_analyst.types.fundamental import FundamentalVisualSummary
from market_analyst.types.news import NewsVisualSummary
from market_analyst.types.supervisor import (
    SupervisorRatingComponent,
    SupervisorVisualComponent,
    SupervisorVisualSummary,
)
from market_analyst.types.technical import TechnicalChartArtifact, TechnicalVisualSummary


def build_fundamental_visual_summary(payload: dict[str, Any], *, rating: int | None) -> FundamentalVisualSummary:
    growth_points = _read_string_list(payload.get("growth"))
    cash_flow_points = _read_string_list(payload.get("cash_flow"))
    debt_points = _read_string_list(payload.get("debt_and_balance_sheet"))
    risk_points = _read_string_list(payload.get("risks"))
    watch_items = _read_string_list(payload.get("watch_items"))
    positives = _unique(growth_points + cash_flow_points + debt_points)[:3]
    if not watch_items and risk_points:
        watch_items = risk_points[:2]
    return FundamentalVisualSummary(
        stance=_read_string(payload.get("stance")) or describe_rating_stance(rating),
        revenue_display=_read_string(payload.get("revenue"))
        or _read_string(payload.get("revenue_display"))
        or _read_string(_read_nested(payload, "metrics", "revenue")),
        revenue_growth_pct=_coerce_percent(
            payload.get("revenue_growth_pct")
            or payload.get("revenue_growth")
            or _read_nested(payload, "metrics", "revenue_growth_pct")
        ),
        profit_margin_pct=_coerce_percent(
            payload.get("profit_margin_pct")
            or payload.get("net_margin_pct")
            or payload.get("operating_margin_pct")
            or _read_nested(payload, "metrics", "profit_margin_pct")
        ),
        debt_to_equity=_coerce_number(payload.get("debt_to_equity") or _read_nested(payload, "metrics", "debt_to_equity")),
        cash_flow_view=_read_string(payload.get("cash_flow_view")) or _first(cash_flow_points),
        valuation_view=_read_string(payload.get("valuation_view"))
        or _read_string(payload.get("business_quality"))
        or _read_string(_read_nested(payload, "metrics", "valuation_view")),
        top_positives=positives,
        top_risks=risk_points[:3],
        watch_items=watch_items[:3],
    )


def build_technical_visual_summary(
    payload: dict[str, Any],
    *,
    rating: int | None,
    artifact: TechnicalChartArtifact,
) -> TechnicalVisualSummary:
    risks = _read_string_list(payload.get("risks"))
    watch_items = _read_string_list(payload.get("watch_items"))
    support_levels = _split_levels(payload.get("support_resistance"), prefix="support")
    resistance_levels = _split_levels(payload.get("support_resistance"), prefix="resistance")
    if not watch_items:
        watch_items = resistance_levels[:1] + support_levels[:1]
    return TechnicalVisualSummary(
        stance=_read_string(payload.get("stance")) or describe_rating_stance(rating),
        trend_state=_read_string(payload.get("trend")),
        momentum_state=_read_string(payload.get("momentum")),
        setup=_read_string(payload.get("setup")) or _read_string(payload.get("support_resistance")),
        current_price=artifact.latest_close,
        rsi=artifact.latest_rsi,
        distance_to_ma20_pct=_distance_pct(artifact.latest_close, artifact.latest_ma20),
        distance_to_ma50_pct=_distance_pct(artifact.latest_close, artifact.latest_ma50),
        macd_signal_state=_infer_macd_signal_state(artifact),
        support_levels=support_levels[:3],
        resistance_levels=resistance_levels[:3],
        top_risks=risks[:3],
        watch_items=watch_items[:3],
    )


def build_news_visual_summary(payload: dict[str, Any], *, rating: int | None) -> NewsVisualSummary:
    positive_points = _read_string_list(payload.get("positive_developments"))
    negative_points = _read_string_list(payload.get("negative_developments"))
    sector_context = _read_string_list(payload.get("sector_context"))
    stock_implications = _read_string_list(payload.get("stock_implications"))
    watch_items = _read_string_list(payload.get("watch_items"))
    return NewsVisualSummary(
        stance=_read_string(payload.get("stance")) or describe_rating_stance(rating),
        sentiment_score=extract_rating(payload, keys=("sentiment_score", "rating", "news_rating", "score")),
        positive_count=len(positive_points),
        negative_count=len(negative_points),
        positive_points=positive_points[:3],
        negative_points=negative_points[:3],
        sector_tailwinds=_classify_sector_points(sector_context, positive=True)[:3],
        sector_headwinds=_classify_sector_points(sector_context, positive=False)[:3],
        watch_items=(watch_items or stock_implications)[:3],
    )


def build_supervisor_visual_summary(
    *,
    final_rating: int,
    summary: str,
    components: list[SupervisorRatingComponent],
    fundamental: FundamentalVisualSummary | None,
    technical: TechnicalVisualSummary | None,
    news: NewsVisualSummary | None,
) -> SupervisorVisualSummary:
    positives = _unique(
        (fundamental.top_positives if fundamental else [])
        + (news.positive_points if news else [])
        + ([technical.trend_state] if technical and technical.trend_state else [])
    )[:4]
    risks = _unique(
        (fundamental.top_risks if fundamental else [])
        + (technical.top_risks if technical else [])
        + (news.negative_points if news else [])
    )[:4]
    watch_items = _unique(
        (fundamental.watch_items if fundamental else [])
        + (technical.watch_items if technical else [])
        + (news.watch_items if news else [])
    )[:4]
    return SupervisorVisualSummary(
        stance=describe_rating_stance(final_rating),
        confidence=_describe_confidence(final_rating, components),
        decision=summary,
        top_positives=positives,
        top_risks=risks,
        watch_items=watch_items,
        component_contributions=_build_component_contributions(components, final_rating),
    )


def describe_rating_stance(rating: int | None) -> str | None:
    if rating is None:
        return None
    if rating >= 75:
        return "Bullish"
    if rating >= 60:
        return "Constructive"
    if rating >= 45:
        return "Neutral"
    if rating >= 30:
        return "Cautious"
    return "High Risk"


def _describe_confidence(final_rating: int, components: list[SupervisorRatingComponent]) -> str:
    available = [component.rating for component in components if component.rating is not None]
    if len(available) < 2:
        return "Medium"
    spread = max(available) - min(available)
    distance = abs(final_rating - 50)
    if spread <= 12 and distance >= 18:
        return "High"
    if spread >= 28 and distance <= 15:
        return "Low"
    return "Medium"


def _build_component_contributions(
    components: list[SupervisorRatingComponent],
    final_rating: int,
) -> list[SupervisorVisualComponent]:
    items: list[SupervisorVisualComponent] = []
    for component in components:
        contribution = None
        if component.rating is not None:
            contribution = round((component.rating - final_rating) * component.weight, 2)
        items.append(
            SupervisorVisualComponent(
                name=component.name,
                rating=component.rating,
                weight_pct=round(component.weight * 100, 1),
                contribution_pct=contribution,
            )
        )
    return items


def _classify_sector_points(points: list[str], *, positive: bool) -> list[str]:
    positive_markers = ("tailwind", "support", "improving", "favorable", "growth", "strong")
    negative_markers = ("headwind", "pressure", "weak", "risk", "slowdown", "adverse")
    markers = positive_markers if positive else negative_markers
    matches = [point for point in points if any(marker in point.lower() for marker in markers)]
    if matches:
        return matches
    return points if positive else []


def _infer_macd_signal_state(artifact: TechnicalChartArtifact) -> str | None:
    macd = artifact.latest_macd
    signal = artifact.latest_macd_signal
    if macd is None or signal is None:
        return None
    if macd > signal:
        return "Bullish Cross"
    if macd < signal:
        return "Bearish Cross"
    return "Neutral"


def _distance_pct(price: float | None, moving_average: float | None) -> float | None:
    if price is None or moving_average in (None, 0):
        return None
    return round(((price - moving_average) / moving_average) * 100, 2)


def _split_levels(value: object, *, prefix: str) -> list[str]:
    text = _read_string(value)
    if not text:
        return []
    matches = re.findall(r"\d+(?:\.\d+)?", text)
    if not matches:
        return [text] if prefix == "support" else []
    midpoint = max(1, len(matches) // 2)
    selected = matches[:midpoint] if prefix == "support" else matches[midpoint:]
    if not selected:
        selected = matches[:2]
    return selected


def _read_nested(payload: dict[str, Any], *path: str) -> object:
    current: object = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _read_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _read_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [item for item in (_read_string(entry) for entry in value) if item]
    item = _read_string(value)
    return [item] if item else []


def _coerce_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if match:
            return float(match.group(0))
    return None


def _coerce_percent(value: object) -> float | None:
    number = _coerce_number(value)
    if number is None:
        return None
    if abs(number) <= 1 and isinstance(value, (int, float)):
        number *= 100
    return round(number, 2)


def _first(values: list[str]) -> str | None:
    return values[0] if values else None


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        key = value.strip()
        if not key:
            continue
        lowered = key.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(key)
    return ordered
