from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NewsSourceReference:
    title: str
    url: str


@dataclass(frozen=True)
class NewsAnalysisRequest:
    company_name: str
    ticker: str
    sector: str | None = None
    question: str | None = None
    time_range: str = "month"
    max_results: int = 8


@dataclass(frozen=True)
class NewsVisualSummary:
    stance: str | None = None
    sentiment_score: int | None = None
    positive_count: int | None = None
    negative_count: int | None = None
    positive_points: list[str] = field(default_factory=list)
    negative_points: list[str] = field(default_factory=list)
    sector_tailwinds: list[str] = field(default_factory=list)
    sector_headwinds: list[str] = field(default_factory=list)
    watch_items: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NewsAnalysisResult:
    company_name: str
    ticker: str
    sector: str | None
    question: str
    answer: str
    rating: int | None = None
    sentiment_score: int | None = None
    sources: list[NewsSourceReference] = field(default_factory=list)
    structured_output: dict[str, Any] = field(default_factory=dict)
    visual_summary: NewsVisualSummary | None = None
