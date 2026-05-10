from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from market_analyst.config.settings import load_settings
from market_analyst.providers.document_intelligence import analyze_report_to_markdown
from market_analyst.types.documents import MarkdownReport, ReportInput


HEADER_SPLITTER = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("#", "company"),
        ("##", "document"),
        ("###", "page"),
        ("####", "section"),
    ],
    strip_headers=False,
)


def discover_reports(reports_dir: Path | str = "reports") -> list[ReportInput]:
    root = Path(reports_dir)
    paths = sorted(root.glob("*.pdf"))
    return [infer_report_input(path) for path in paths]


def infer_report_input(path: Path) -> ReportInput:
    stem = path.stem.replace("_", " ").replace("-", " ")
    words = [word for word in stem.split() if word.lower() not in {"annual", "report", "fy", "pdf"}]
    company_name = " ".join(word.capitalize() for word in words) or path.stem
    ticker = re.sub(r"[^A-Z0-9]", "", company_name.upper())[:16] or "UNKNOWN"
    return ReportInput(path=path, company_name=company_name, ticker=ticker)


def load_report_as_markdown(report: ReportInput, max_pages: int | None = None) -> MarkdownReport:
    settings = load_settings()
    return analyze_report_to_markdown(settings, report, max_pages=max_pages)


def build_markdown_reports(
    reports: Iterable[ReportInput],
    max_pages: int | None = None,
) -> list[MarkdownReport]:
    settings = load_settings()
    return [analyze_report_to_markdown(settings, report, max_pages=max_pages) for report in reports]


def split_markdown_report(
    markdown_report: MarkdownReport,
    chunk_size: int = 1400,
    chunk_overlap: int = 180,
) -> list[Document]:
    header_documents = HEADER_SPLITTER.split_text(markdown_report.markdown)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    split_documents = splitter.split_documents(header_documents)

    chunks: list[Document] = []
    for index, doc in enumerate(split_documents):
        metadata = dict(doc.metadata)
        metadata.update(
            {
                "source_path": str(markdown_report.report.path),
                "source_file": markdown_report.report.path.name,
                "company_name": markdown_report.report.company_name,
                "ticker": markdown_report.report.ticker,
                "filing_type": markdown_report.report.filing_type,
                "chunk_index": index,
                "page_number": _parse_page_number(metadata.get("page")),
            }
        )
        content = doc.page_content.strip()
        chunk_id = _chunk_id(markdown_report.report, index, content)
        metadata["chunk_id"] = chunk_id
        metadata["heading_path"] = _heading_path(metadata)
        chunks.append(Document(id=chunk_id, page_content=content, metadata=metadata))
    return chunks


def build_header_chunks(
    markdown_reports: Iterable[MarkdownReport],
    chunk_size: int = 1400,
    chunk_overlap: int = 180,
) -> list[Document]:
    chunks: list[Document] = []
    for markdown_report in markdown_reports:
        chunks.extend(
            split_markdown_report(
                markdown_report,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )
    return chunks


def _parse_page_number(page_label: object) -> int | None:
    if not page_label:
        return None
    match = re.search(r"\d+", str(page_label))
    return int(match.group(0)) if match else None


def _chunk_id(report: ReportInput, index: int, content: str) -> str:
    raw = f"{report.path.resolve()}|{index}|{content[:256]}".encode("utf-8", errors="ignore")
    digest = hashlib.sha1(raw).hexdigest()[:16]
    return f"{report.ticker.lower()}-{index:05d}-{digest}"


def _heading_path(metadata: dict[str, object]) -> str:
    parts = [metadata.get("company"), metadata.get("document"), metadata.get("page"), metadata.get("section")]
    return " > ".join(str(part) for part in parts if part)
