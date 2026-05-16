from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NewsAnalysisRequest:
    company_name: str
    ticker: str
    sector: str | None = None
    question: str | None = None
    time_range: str = "month"
    max_results: int = 8


@dataclass(frozen=True)
class NewsAnalysisResult:
    company_name: str
    ticker: str
    sector: str | None
    question: str
    answer: str
    rating: int | None = None
    sentiment_score: int | None = None
