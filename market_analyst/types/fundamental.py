from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FundamentalAnalysisRequest:
    company_name: str
    ticker: str | None = None
    document_id: str | None = None
    question: str | None = None
    retrieval_limit: int = 5


@dataclass(frozen=True)
class FundamentalAnalysisResult:
    company_name: str
    ticker: str | None
    question: str
    answer: str
    rating: int | None
