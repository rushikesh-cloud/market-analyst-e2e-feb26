from market_analyst.services.agents.news import (
    build_news_analysis_prompt,
    extract_sentiment_score,
    parse_json_object,
)
from market_analyst.types.news import NewsAnalysisRequest


def test_build_news_analysis_prompt_includes_company_sector_and_search_instructions() -> None:
    prompt = build_news_analysis_prompt(
        request=NewsAnalysisRequest(
            company_name="Sample Bank",
            ticker="SAMPLE",
            sector="Banking",
            time_range="week",
        ),
        question="Find recent good and bad news.",
    )

    assert "Company: Sample Bank" in prompt
    assert "Ticker: SAMPLE" in prompt
    assert "Sector: Banking" in prompt
    assert "Run one company/ticker news search" in prompt
    assert "Run one sector-context news search" in prompt


def test_parse_json_object_handles_fenced_json_and_score() -> None:
    payload = parse_json_object(
        """```json
        {"sentiment_score": "67", "positive_developments": ["new order win"]}
        ```"""
    )

    assert payload["positive_developments"] == ["new order win"]
    assert extract_sentiment_score(payload) == 67


def test_extract_sentiment_score_clamps_numeric_values() -> None:
    assert extract_sentiment_score({"sentiment_score": 120}) == 100
    assert extract_sentiment_score({"sentiment_score": -10}) == 0
    assert extract_sentiment_score({"sentiment_score": True}) is None
