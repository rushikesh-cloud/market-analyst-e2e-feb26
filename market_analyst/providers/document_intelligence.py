from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

import fitz
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentContentFormat
from azure.core.credentials import AzureKeyCredential

from market_analyst.config.settings import Settings
from market_analyst.types.documents import MarkdownReport, ReportInput


def build_document_intelligence_client(settings: Settings) -> DocumentIntelligenceClient:
    settings.require_document_intelligence()
    return DocumentIntelligenceClient(
        endpoint=settings.document_intelligence_endpoint,
        credential=AzureKeyCredential(settings.document_intelligence_key),
    )


def analyze_report_to_markdown(
    client: DocumentIntelligenceClient,
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

    for page_offset, document_bytes in _iter_pdf_batches(report.path, max_pages=max_pages, batch_pages=batch_pages):
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            body=document_bytes,
            output_content_format=DocumentContentFormat.MARKDOWN,
            content_type="application/octet-stream",
        )
        result: AnalyzeResult = poller.result()
        sections.extend(_page_sections_from_result(result, page_offset=page_offset))
        page_count += len(result.pages or [])

    markdown = "\n".join(sections).strip() + "\n"
    return MarkdownReport(report=report, markdown=markdown, page_count=page_count)


def _page_sections_from_result(result: AnalyzeResult, page_offset: int) -> list[str]:
    content = result.content or ""
    sections: list[str] = []

    if result.pages:
        for page in result.pages:
            page_markdown = _normalize_page_markdown(_slice_page_content(content, page.spans)).strip()
            sections.append(f"### Page {page_offset + int(page.page_number)}")
            if page_markdown:
                sections.append(page_markdown)
            sections.append("")
    elif content.strip():
        sections.append("### Document")
        sections.append(content.strip())
        sections.append("")

    return sections


def _iter_pdf_batches(path: Path, max_pages: int | None, batch_pages: int) -> list[tuple[int, BytesIO]]:
    if batch_pages < 1:
        raise ValueError("batch_pages must be at least 1")

    source_pdf = fitz.open(path)
    total_pages = source_pdf.page_count
    selected_pages = total_pages if max_pages is None else min(max_pages, total_pages)

    batches: list[tuple[int, BytesIO]] = []
    try:
        for start in range(0, selected_pages, batch_pages):
            end = min(start + batch_pages, selected_pages)
            batch_pdf = fitz.open()
            try:
                batch_pdf.insert_pdf(source_pdf, from_page=start, to_page=end - 1)
                buffer = BytesIO(batch_pdf.tobytes(garbage=4, deflate=True))
                buffer.seek(0)
                batches.append((start, buffer))
            finally:
                batch_pdf.close()
        return batches
    finally:
        source_pdf.close()


def _slice_page_content(content: str, spans: list[object] | None) -> str:
    if not spans:
        return content
    parts = []
    for span in spans:
        offset = int(getattr(span, "offset", 0) or 0)
        length = int(getattr(span, "length", 0) or 0)
        if length <= 0:
            continue
        parts.append(content[offset : offset + length])
    return "\n".join(parts)


def _normalize_page_markdown(markdown: str) -> str:
    lines = []
    for line in markdown.splitlines():
        lines.append(re.sub(r"^(#{1,6})\s+", "#### ", line))
    return "\n".join(lines)
