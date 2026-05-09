from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from market_analyst.types.documents import ChunkRecord, MarkdownReport, ReportInput


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
    loader = PyPDFLoader(str(report.path))
    pages = loader.load()
    if max_pages is not None:
        pages = pages[:max_pages]

    sections = [
        f"# {report.company_name}",
        f"## {report.path.name}",
        "",
    ]
    for index, page in enumerate(pages, start=1):
        text = page.page_content or ""
        sections.append(f"### Page {index}")
        sections.append(_page_text_to_markdown(text))
        sections.append("")

    return MarkdownReport(report=report, markdown="\n".join(sections).strip() + "\n", page_count=len(pages))


def build_markdown_reports(
    reports: Iterable[ReportInput],
    max_pages: int | None = None,
) -> list[MarkdownReport]:
    return [load_report_as_markdown(report, max_pages=max_pages) for report in reports]


def split_markdown_report(
    markdown_report: MarkdownReport,
    chunk_size: int = 1400,
    chunk_overlap: int = 180,
) -> list[ChunkRecord]:
    header_documents = HEADER_SPLITTER.split_text(markdown_report.markdown)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    split_documents = splitter.split_documents(header_documents)

    chunks: list[ChunkRecord] = []
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
        chunks.append(ChunkRecord(chunk_id=chunk_id, content=content, metadata=metadata))
    return chunks


def build_header_chunks(
    markdown_reports: Iterable[MarkdownReport],
    chunk_size: int = 1400,
    chunk_overlap: int = 180,
) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    for markdown_report in markdown_reports:
        chunks.extend(
            split_markdown_report(
                markdown_report,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )
    return chunks


def to_langchain_documents(chunks: Iterable[ChunkRecord]) -> list[Document]:
    return [Document(page_content=chunk.content, metadata=chunk.metadata) for chunk in chunks]


def _page_text_to_markdown(text: str) -> str:
    lines = [_clean_line(line) for line in text.splitlines()]
    output: list[str] = []
    previous_blank = True
    for line in lines:
        if not line:
            if not previous_blank:
                output.append("")
            previous_blank = True
            continue
        if _looks_like_heading(line):
            output.append(f"#### {line}")
        else:
            output.append(line)
        previous_blank = False
    return "\n".join(output).strip()


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _looks_like_heading(line: str) -> bool:
    if len(line) < 4 or len(line) > 100:
        return False
    if line.endswith((".", ",", ";", ":")) and len(line.split()) > 8:
        return False
    letters = [char for char in line if char.isalpha()]
    if len(letters) < 3:
        return False
    upper_ratio = sum(char.isupper() for char in letters) / len(letters)
    if upper_ratio >= 0.65:
        return True
    if re.match(r"^(\d+(\.\d+)*|[A-Z])[\).:\-]\s+\w+", line):
        return True
    words = line.split()
    title_case_words = sum(1 for word in words if word[:1].isupper())
    return 2 <= len(words) <= 8 and title_case_words >= max(2, len(words) - 1)


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
