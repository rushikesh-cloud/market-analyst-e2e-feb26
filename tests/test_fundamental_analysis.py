from market_analyst.services.agents.fundamental import (
    build_fundamental_analysis_prompt,
    compile_fundamental_sources,
    normalize_fundamental_ticker,
)
from market_analyst.types.fundamental import FundamentalAnalysisRequest


def test_fundamental_prompt_requires_rag_and_rating() -> None:
    prompt = build_fundamental_analysis_prompt(
        request=FundamentalAnalysisRequest(company_name="Sample Bank", ticker="SAMPLE"),
        question="Assess fundamentals.",
    )

    assert "Company: Sample Bank" in prompt
    assert "Fundamental RAG ticker: SAMPLE" in prompt
    assert "Search annual-report RAG context" in prompt
    assert "fundamental_rating from 1 to 100" in prompt


def test_fundamental_ticker_normalization_strips_exchange_suffix() -> None:
    assert normalize_fundamental_ticker("RELIANCE.NS") == "RELIANCE"
    assert normalize_fundamental_ticker(" tcs.bo ") == "TCS"
    assert normalize_fundamental_ticker("INFY") == "INFY"
    assert normalize_fundamental_ticker("") is None


def test_fundamental_prompt_shows_normalized_and_original_ticker() -> None:
    prompt = build_fundamental_analysis_prompt(
        request=FundamentalAnalysisRequest(company_name="Reliance", ticker="RELIANCE.NS"),
        question="Assess fundamentals.",
    )

    assert "Fundamental RAG ticker: RELIANCE" in prompt
    assert "Original ticker input: RELIANCE.NS" in prompt
    assert "exchange suffixes such as `.NS`" in prompt


def test_compile_fundamental_sources_dedupes_and_formats(monkeypatch) -> None:
    monkeypatch.setattr(
        "market_analyst.services.agents.fundamental.hybrid_search",
        lambda *args, **kwargs: [
            {
                "metadata": {
                    "source_file": "annual-report.pdf",
                    "page_number": 12,
                    "heading_path": "Bank > Annual Report > Page 12 > Risks",
                    "source_path": "uploads/bank/annual-report.pdf",
                    "chunk_id": "chunk-1",
                }
            },
            {
                "metadata": {
                    "source_file": "annual-report.pdf",
                    "page_number": 12,
                    "heading_path": "Bank > Annual Report > Page 12 > Risks",
                    "source_path": "uploads/bank/annual-report.pdf",
                    "chunk_id": "chunk-1",
                }
            },
        ],
    )

    sources = compile_fundamental_sources(
        settings=None,  # type: ignore[arg-type]
        query="Assess fundamentals",
        ticker="BANK",
        document_id="doc-1",
        limit=5,
    )

    assert len(sources) == 1
    assert sources[0].document_name == "annual-report.pdf"
    assert sources[0].page_number == 12
