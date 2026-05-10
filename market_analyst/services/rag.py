from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable, NamedTuple

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

HTML_TABLE_PATTERN = re.compile(r"<table\b.*?</table>", re.IGNORECASE | re.DOTALL)
PIPE_TABLE_ROW_PATTERN = re.compile(r"^\s*\|.*\|\s*$")
PIPE_TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
TABLE_CONTEXT_CHARS = 360


class _TableBlock(NamedTuple):
    start: int
    end: int
    content: str
    table_format: str


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
    split_documents = [
        split_doc
        for doc in header_documents
        for split_doc in _split_document_preserving_tables(
            doc,
            splitter=splitter,
            table_context_chars=TABLE_CONTEXT_CHARS,
            target_chunk_size=chunk_size,
        )
    ]

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


def _split_document_preserving_tables(
    document: Document,
    splitter: RecursiveCharacterTextSplitter,
    table_context_chars: int,
    target_chunk_size: int,
) -> list[Document]:
    table_blocks = _find_table_blocks(document.page_content)
    if not table_blocks:
        return splitter.split_documents([document])

    split_documents: list[Document] = []
    cursor = 0

    for table_index, table in enumerate(table_blocks):
        before_text = document.page_content[cursor : table.start]
        split_documents.extend(_split_plain_text(before_text, document, splitter))

        after_end = table_blocks[table_index + 1].start if table_index + 1 < len(table_blocks) else len(document.page_content)
        after_text = document.page_content[table.end : after_end]
        table_content = "\n\n".join(
            part
            for part in (
                _tail_context(before_text, table_context_chars),
                table.content.strip(),
                _head_context(after_text, table_context_chars),
            )
            if part
        )
        metadata = dict(document.metadata)
        metadata.update(
            {
                "contains_table": True,
                "table_index": table_index,
                "table_format": table.table_format,
                "table_char_length": len(table.content),
                "chunk_exceeds_target_size": len(table_content) > target_chunk_size,
            }
        )
        split_documents.append(Document(page_content=table_content, metadata=metadata))
        cursor = table.end

    trailing_text = document.page_content[cursor:]
    split_documents.extend(_split_plain_text(trailing_text, document, splitter))
    return [doc for doc in split_documents if doc.page_content.strip()]


def _split_plain_text(
    text: str,
    source_document: Document,
    splitter: RecursiveCharacterTextSplitter,
) -> list[Document]:
    stripped_text = text.strip()
    if not stripped_text:
        return []
    return splitter.split_documents([Document(page_content=stripped_text, metadata=dict(source_document.metadata))])


def _find_table_blocks(markdown: str) -> list[_TableBlock]:
    blocks = [
        _TableBlock(match.start(), match.end(), match.group(0), "html")
        for match in HTML_TABLE_PATTERN.finditer(markdown)
    ]
    blocks.extend(_find_pipe_table_blocks(markdown))
    return _dedupe_table_blocks(blocks)


def _find_pipe_table_blocks(markdown: str) -> list[_TableBlock]:
    blocks: list[_TableBlock] = []
    line_start = 0
    lines = markdown.splitlines(keepends=True)
    line_offsets: list[tuple[int, str]] = []
    for line in lines:
        line_offsets.append((line_start, line))
        line_start += len(line)

    index = 0
    while index + 1 < len(line_offsets):
        _, current_line = line_offsets[index]
        _, next_line = line_offsets[index + 1]
        if not PIPE_TABLE_ROW_PATTERN.match(current_line) or not PIPE_TABLE_SEPARATOR_PATTERN.match(next_line):
            index += 1
            continue

        start = line_offsets[index][0]
        end_index = index + 2
        while end_index < len(line_offsets) and PIPE_TABLE_ROW_PATTERN.match(line_offsets[end_index][1]):
            end_index += 1
        end = line_offsets[end_index][0] if end_index < len(line_offsets) else len(markdown)
        blocks.append(_TableBlock(start, end, markdown[start:end], "markdown_pipe"))
        index = end_index

    return blocks


def _dedupe_table_blocks(blocks: list[_TableBlock]) -> list[_TableBlock]:
    deduped: list[_TableBlock] = []
    for block in sorted(blocks, key=lambda item: (item.start, item.end)):
        if deduped and block.start < deduped[-1].end:
            continue
        deduped.append(block)
    return deduped


def _tail_context(text: str, max_chars: int) -> str:
    return _trim_context(text[-max_chars:])


def _head_context(text: str, max_chars: int) -> str:
    return _trim_context(text[:max_chars])


def _trim_context(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _chunk_id(report: ReportInput, index: int, content: str) -> str:
    raw = f"{report.path.resolve()}|{index}|{content[:256]}".encode("utf-8", errors="ignore")
    digest = hashlib.sha1(raw).hexdigest()[:16]
    return f"{report.ticker.lower()}-{index:05d}-{digest}"


def _heading_path(metadata: dict[str, object]) -> str:
    parts = [metadata.get("company"), metadata.get("document"), metadata.get("page"), metadata.get("section")]
    return " > ".join(str(part) for part in parts if part)
