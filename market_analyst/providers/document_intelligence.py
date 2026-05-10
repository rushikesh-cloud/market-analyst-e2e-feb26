from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import Iterator

import fitz
from langchain_community.document_loaders import AzureAIDocumentIntelligenceLoader
from langchain_core.documents import Document

from market_analyst.config.settings import Settings
from market_analyst.types.documents import MarkdownReport, ReportInput


def build_document_intelligence_loader(
    settings: Settings,
    document_bytes: bytes,
) -> AzureAIDocumentIntelligenceLoader:
    settings.require_document_intelligence()
    return AzureAIDocumentIntelligenceLoader(
        api_endpoint=settings.document_intelligence_endpoint,
        api_key=settings.document_intelligence_key,
        bytes_source=document_bytes,
        api_model="prebuilt-layout",
        mode="markdown",
    )


def analyze_report_to_markdown(
    settings: Settings,
    report: ReportInput,
    max_pages: int | None = None,
    batch_pages: int = 10,
) -> MarkdownReport:
    sections = [
        f"# {report.company_name}",
        f"## {report.path.name}",
        "",
    ]
    page_count = 0

    for page_offset, page_total, document_bytes in _iter_pdf_batches(
        report.path,
        max_pages=max_pages,
        batch_pages=batch_pages,
    ):
        loader = build_document_intelligence_loader(settings, document_bytes.getvalue())
        sections.extend(_page_sections_from_documents(loader.load(), page_offset=page_offset))
        page_count += page_total

    markdown = "\n".join(sections).strip() + "\n"
    return MarkdownReport(report=report, markdown=markdown, page_count=page_count)


def _page_sections_from_documents(documents: list[Document], page_offset: int) -> list[str]:
    if len(documents) == 1 and documents[0].metadata.get("pages"):
        return list(_sections_from_markdown_document(documents[0], page_offset=page_offset))

    if not documents:
        return ["### Document", ""]

    return [
        section
        for index, document in enumerate(documents, start=1)
        for section in _section(
            page_number=_document_page_number(document, default=page_offset + index),
            content=document.page_content,
        )
    ]


def _sections_from_markdown_document(document: Document, page_offset: int) -> Iterator[str]:
    for page in document.metadata["pages"]:
        page_number = page_offset + int(page.get("page_number") or 0)
        content = _slice_page_content(document.page_content, page.get("spans"))
        yield from _section(page_number=page_number, content=content)


def _section(page_number: int, content: str) -> Iterator[str]:
    yield f"### Page {page_number}"
    page_markdown = _normalize_page_markdown(content).strip()
    if page_markdown:
        yield page_markdown
    yield ""


def _slice_page_content(content: str, spans: list[dict[str, object]] | None) -> str:
    if not spans:
        return content
    parts = []
    for span in spans:
        offset = int(span.get("offset") or 0)
        length = int(span.get("length") or 0)
        if length <= 0:
            continue
        parts.append(content[offset : offset + length])
    return "\n".join(parts)


def _iter_pdf_batches(path: Path, max_pages: int | None, batch_pages: int) -> Iterator[tuple[int, int, BytesIO]]:
    if batch_pages < 1:
        raise ValueError("batch_pages must be at least 1")

    source_pdf = fitz.open(path)
    total_pages = source_pdf.page_count
    selected_pages = total_pages if max_pages is None else min(max_pages, total_pages)

    try:
        for start in range(0, selected_pages, batch_pages):
            end = min(start + batch_pages, selected_pages)
            batch_pdf = fitz.open()
            try:
                batch_pdf.insert_pdf(source_pdf, from_page=start, to_page=end - 1)
                buffer = BytesIO(batch_pdf.tobytes(garbage=4, deflate=True))
                buffer.seek(0)
                yield start, end - start, buffer
            finally:
                batch_pdf.close()
    finally:
        source_pdf.close()


def _document_page_number(document: Document, default: int) -> int:
    for key in ("page", "page_number"):
        value = document.metadata.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            match = re.search(r"\d+", value)
            if match:
                return int(match.group(0))
    return default


def _normalize_page_markdown(markdown: str) -> str:
    lines = []
    for line in markdown.splitlines():
        lines.append(re.sub(r"^(#{1,6})\s+", "#### ", line))
    return "\n".join(lines)
