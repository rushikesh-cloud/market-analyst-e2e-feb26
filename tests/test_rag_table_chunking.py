from pathlib import Path

from market_analyst.services.rag import split_markdown_report
from market_analyst.types.documents import MarkdownReport, ReportInput


def _report(markdown: str) -> MarkdownReport:
    return MarkdownReport(
        report=ReportInput(
            path=Path("reports/sample.pdf"),
            company_name="Sample Bank",
            ticker="SAMPLE",
        ),
        markdown=markdown,
        page_count=1,
    )


def test_html_table_stays_in_one_chunk_with_context() -> None:
    markdown = """
# Sample Bank
## sample.pdf
### Page 1
#### Capital
This paragraph explains the capital position before the table and should overlap.

<table>
<tr><th>Metric</th><th>FY2025</th></tr>
<tr><td>CET1</td><td>14.8%</td></tr>
<tr><td>Tier 1</td><td>16.1%</td></tr>
</table>

This paragraph explains the capital movement after the table and should overlap.
"""

    chunks = split_markdown_report(_report(markdown), chunk_size=120, chunk_overlap=20)
    table_chunks = [chunk for chunk in chunks if chunk.metadata.get("contains_table")]

    assert len(table_chunks) == 1
    table_chunk = table_chunks[0]
    assert table_chunk.page_content.count("<table>") == 1
    assert table_chunk.page_content.count("</table>") == 1
    assert "before the table and should overlap" in table_chunk.page_content
    assert "after the table and should overlap" in table_chunk.page_content
    assert table_chunk.metadata["table_format"] == "html"


def test_large_table_can_exceed_chunk_target_without_being_split() -> None:
    rows = "\n".join(f"<tr><td>Metric {index}</td><td>{index}</td></tr>" for index in range(30))
    markdown = f"""
# Sample Bank
## sample.pdf
### Page 1
#### Liquidity
Opening context for liquidity metrics.

<table>
{rows}
</table>

Closing context for liquidity metrics.
"""

    chunks = split_markdown_report(_report(markdown), chunk_size=180, chunk_overlap=20)
    table_chunks = [chunk for chunk in chunks if chunk.metadata.get("contains_table")]

    assert len(table_chunks) == 1
    assert table_chunks[0].page_content.count("<tr>") == 30
    assert table_chunks[0].metadata["chunk_exceeds_target_size"] is True


def test_markdown_pipe_table_stays_in_one_chunk() -> None:
    markdown = """
# Sample Bank
## sample.pdf
### Page 1
#### Deposits
Deposit mix context before table.

| Segment | Share |
| --- | --- |
| Retail | 64% |
| Corporate | 36% |

Deposit mix context after table.
"""

    chunks = split_markdown_report(_report(markdown), chunk_size=90, chunk_overlap=10)
    table_chunks = [chunk for chunk in chunks if chunk.metadata.get("contains_table")]

    assert len(table_chunks) == 1
    assert "| Retail | 64% |" in table_chunks[0].page_content
    assert "| Corporate | 36% |" in table_chunks[0].page_content
    assert table_chunks[0].metadata["table_format"] == "markdown_pipe"
