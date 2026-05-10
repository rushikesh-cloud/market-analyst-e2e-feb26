from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.documents import Document


@dataclass(frozen=True)
class ReportInput:
    path: Path
    company_name: str
    ticker: str
    filing_type: str = "annual_report"


@dataclass(frozen=True)
class MarkdownReport:
    report: ReportInput
    markdown: str
    page_count: int


@dataclass(frozen=True)
class IngestionResult:
    markdown_reports: list[MarkdownReport]
    chunks: list[Document]
    vector_ids: list[str] = field(default_factory=list)
    reports_rows: int = 0

    @property
    def report_count(self) -> int:
        return len(self.markdown_reports)

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)
