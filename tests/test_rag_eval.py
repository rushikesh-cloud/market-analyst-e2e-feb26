from pathlib import Path

from market_analyst.services.rag_eval import (
    build_broad_eval_chunks,
    load_rag_eval_cases,
)
from market_analyst.types.documents import MarkdownReport, ReportInput


def _report(markdown: str, name: str = "sample_report.pdf") -> MarkdownReport:
    return MarkdownReport(
        report=ReportInput(path=Path(name), company_name="Sample Co", ticker="SAMPLE"),
        markdown=markdown,
        page_count=6,
    )


def test_build_broad_eval_chunks_groups_consecutive_pages() -> None:
    markdown = """
# Sample Co
## sample_report.pdf

### Page 1
alpha

### Page 2
beta

### Page 3
gamma

### Page 4
delta

### Page 5
epsilon

### Page 6
zeta
"""
    chunks = build_broad_eval_chunks([_report(markdown)], target_chunks_per_report=3)

    assert len(chunks) == 3
    assert [(chunk.start_page, chunk.end_page) for chunk in chunks] == [(1, 2), (3, 4), (5, 6)]
    assert chunks[0].page_count == 2


def test_load_rag_eval_cases_reads_curated_dataset() -> None:
    cases = load_rag_eval_cases()

    assert len(cases) == 10
    assert {case.company_name for case in cases} == {"Bandhan", "Emcure"}
