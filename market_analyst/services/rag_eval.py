from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from market_analyst.services.rag import build_markdown_reports, discover_reports
from market_analyst.types.documents import MarkdownReport, ReportInput


TARGET_EVAL_REPORTS = (
    "bandhan_annual_report.pdf",
    "emcure_annual_report.pdf",
)


@dataclass(frozen=True)
class EvalChunkWindow:
    company_name: str
    report_file: str
    chunk_index: int
    start_page: int
    end_page: int
    page_count: int
    character_count: int
    content: str


@dataclass(frozen=True)
class RagEvalCase:
    case_id: str
    company_name: str
    report_file: str
    question_style: str
    evaluation_focus: str
    question: str
    expected_answer: str
    key_facts: list[str]
    source_pages: list[int]


def discover_eval_reports(reports_dir: Path | str = "reports") -> list[ReportInput]:
    reports = discover_reports(reports_dir)
    allowed = set(TARGET_EVAL_REPORTS)
    return [report for report in reports if report.path.name in allowed]


def build_eval_markdown_reports(
    reports_dir: Path | str = "reports",
    max_pages: int | None = None,
) -> list[MarkdownReport]:
    return build_markdown_reports(discover_eval_reports(reports_dir), max_pages=max_pages)


def export_markdown_reports(
    markdown_reports: Iterable[MarkdownReport],
    output_dir: Path | str,
) -> list[Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for markdown_report in markdown_reports:
        path = root / f"{markdown_report.report.path.stem}.md"
        path.write_text(markdown_report.markdown, encoding="utf-8")
        written.append(path)
    return written


def build_broad_eval_chunks(
    markdown_reports: Iterable[MarkdownReport],
    target_chunks_per_report: int = 5,
) -> list[EvalChunkWindow]:
    if target_chunks_per_report < 1:
        raise ValueError("target_chunks_per_report must be at least 1")

    windows: list[EvalChunkWindow] = []
    for markdown_report in markdown_reports:
        page_sections = _split_markdown_pages(markdown_report.markdown)
        if not page_sections:
            continue

        chunk_size = max(1, (len(page_sections) + target_chunks_per_report - 1) // target_chunks_per_report)
        report_windows = [
            _build_chunk_window(markdown_report, index, group)
            for index, group in enumerate(_group_page_sections(page_sections, chunk_size))
        ]
        windows.extend(report_windows)
    return windows


def load_rag_eval_cases(path: Path | str = "data/evals/fundamental_rag_eval_cases.json") -> list[RagEvalCase]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [RagEvalCase(**row) for row in payload]


def eval_cases_as_rows(cases: Iterable[RagEvalCase]) -> list[dict[str, object]]:
    return [asdict(case) for case in cases]


def eval_chunks_as_rows(chunks: Iterable[EvalChunkWindow]) -> list[dict[str, object]]:
    return [asdict(chunk) for chunk in chunks]


def _split_markdown_pages(markdown: str) -> list[tuple[int, str]]:
    pattern = re.compile(r"^### Page (\d+)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(markdown))
    if not matches:
        return []

    sections: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        page_number = int(match.group(1))
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        section = markdown[start:end].strip()
        if section:
            sections.append((page_number, section))
    return sections


def _group_page_sections(
    page_sections: list[tuple[int, str]],
    group_size: int,
) -> list[list[tuple[int, str]]]:
    return [
        page_sections[index : index + group_size]
        for index in range(0, len(page_sections), group_size)
    ]


def _build_chunk_window(
    markdown_report: MarkdownReport,
    chunk_index: int,
    sections: list[tuple[int, str]],
) -> EvalChunkWindow:
    start_page = sections[0][0]
    end_page = sections[-1][0]
    content = "\n\n".join(section for _, section in sections).strip()
    return EvalChunkWindow(
        company_name=markdown_report.report.company_name,
        report_file=markdown_report.report.path.name,
        chunk_index=chunk_index,
        start_page=start_page,
        end_page=end_page,
        page_count=len(sections),
        character_count=len(content),
        content=content,
    )
