from market_analyst.services.agents.fundamental import build_fundamental_analysis_prompt
from market_analyst.types.fundamental import FundamentalAnalysisRequest


def test_fundamental_prompt_requires_rag_and_rating() -> None:
    prompt = build_fundamental_analysis_prompt(
        request=FundamentalAnalysisRequest(company_name="Sample Bank", ticker="SAMPLE"),
        question="Assess fundamentals.",
    )

    assert "Company: Sample Bank" in prompt
    assert "Ticker: SAMPLE" in prompt
    assert "Search annual-report RAG context" in prompt
    assert "fundamental_rating from 1 to 100" in prompt
