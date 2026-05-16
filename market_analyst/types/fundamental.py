from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FundamentalSourceReference:
    document_name: str | None
    page_number: int | None
    heading_path: str | None
    source_path: str | None
    chunk_id: str | None


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
    sources: list[FundamentalSourceReference] = field(default_factory=list)
