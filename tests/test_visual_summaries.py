from pathlib import Path

from market_analyst.services.supervisor import aggregate_supervisor_result
from market_analyst.services.visual_summaries import (
    build_fundamental_visual_summary,
    build_news_visual_summary,
    build_technical_visual_summary,
    describe_rating_stance,
)
from market_analyst.types.fundamental import FundamentalAnalysisResult
from market_analyst.types.news import NewsAnalysisResult
from market_analyst.types.technical import TechnicalAnalysisResult, TechnicalChartArtifact


def _technical_artifact() -> TechnicalChartArtifact:
    return TechnicalChartArtifact(
        ticker="SAMPLE",
        chart_path=Path("notebooks/outputs/sample.png"),
        observation_count=120,
        start_date="2026-01-01",
        end_date="2026-05-01",
        latest_close=110.0,
        latest_ma20=105.0,
        latest_ma50=100.0,
        latest_rsi=62.5,
        latest_macd=1.2,
        latest_macd_signal=0.8,
        latest_macd_histogram=0.4,
        metadata={},
    )


def test_build_fundamental_visual_summary_maps_key_metrics() -> None:
    summary = build_fundamental_visual_summary(
        {
            "stance": "Constructive",
            "revenue": "INR 12,400 Cr",
            "revenue_growth_pct": 14.8,
            "profit_margin_pct": 18.2,
            "debt_to_equity": 0.7,
            "growth": ["Loan growth remains healthy."],
            "cash_flow": ["Operating cash flow remains stable."],
            "debt_and_balance_sheet": ["Capital position remains adequate."],
            "valuation_view": "Valuation remains reasonable.",
            "risks": ["Credit cost normalization remains a risk."],
            "watch_items": ["Monitor NIM trend."],
        },
        rating=68,
    )

    assert summary.stance == "Constructive"
    assert summary.revenue_display == "INR 12,400 Cr"
    assert summary.revenue_growth_pct == 14.8
    assert summary.profit_margin_pct == 18.2
    assert summary.debt_to_equity == 0.7
    assert summary.top_positives == [
        "Loan growth remains healthy.",
        "Operating cash flow remains stable.",
        "Capital position remains adequate.",
    ]
    assert summary.top_risks == ["Credit cost normalization remains a risk."]
    assert summary.watch_items == ["Monitor NIM trend."]


def test_build_technical_visual_summary_uses_artifact_metrics() -> None:
    summary = build_technical_visual_summary(
        {
            "trend": "Uptrend intact.",
            "momentum": "Momentum remains positive.",
            "setup": "Breakout retest possible.",
            "support_resistance": "Support near 104 and 101. Resistance near 113 and 118.",
            "risks": ["Momentum could fade if RSI falls back below 50."],
            "watch_items": ["Watch reaction near 113."],
        },
        rating=74,
        artifact=_technical_artifact(),
    )

    assert summary.stance == "Constructive"
    assert summary.current_price == 110.0
    assert summary.rsi == 62.5
    assert summary.distance_to_ma20_pct == 4.76
    assert summary.distance_to_ma50_pct == 10.0
    assert summary.macd_signal_state == "Bullish Cross"
    assert summary.watch_items == ["Watch reaction near 113."]
    assert summary.top_risks == ["Momentum could fade if RSI falls back below 50."]


def test_build_news_visual_summary_counts_and_buckets_points() -> None:
    summary = build_news_visual_summary(
        {
            "sentiment_score": 61,
            "positive_developments": ["Growth in deposits improved."],
            "negative_developments": ["Margin pressure remains a risk."],
            "sector_context": ["Sector tailwind from improving credit demand."],
            "watch_items": ["Track next quarter commentary."],
        },
        rating=61,
    )

    assert summary.stance == "Constructive"
    assert summary.sentiment_score == 61
    assert summary.positive_count == 1
    assert summary.negative_count == 1
    assert summary.sector_tailwinds == ["Sector tailwind from improving credit demand."]
    assert summary.watch_items == ["Track next quarter commentary."]


def test_aggregate_supervisor_result_builds_visual_summary() -> None:
    fundamental = FundamentalAnalysisResult(
        "Sample Bank",
        "SAMPLE",
        "q",
        "fundamental answer",
        82,
        visual_summary=build_fundamental_visual_summary(
            {
                "growth": ["Revenue growth remains healthy."],
                "risks": ["Provisioning could rise."],
                "watch_items": ["Monitor credit costs."],
            },
            rating=82,
        ),
    )
    technical = TechnicalAnalysisResult(
        "SAMPLE",
        "q",
        "technical answer",
        70,
        chart_path=Path("chart.png"),
        artifact=_technical_artifact(),
        visual_summary=build_technical_visual_summary(
            {"trend": "Trend remains constructive.", "risks": ["Resistance near 113."]},
            rating=70,
            artifact=_technical_artifact(),
        ),
    )
    news = NewsAnalysisResult(
        "Sample Bank",
        "SAMPLE",
        "Banking",
        "q",
        "news answer",
        rating=58,
        sentiment_score=58,
        visual_summary=build_news_visual_summary(
            {
                "positive_developments": ["Deposit growth improved."],
                "negative_developments": ["Margin pressure persists."],
                "watch_items": ["Track management commentary."],
            },
            rating=58,
        ),
    )

    result = aggregate_supervisor_result(
        company_name="Sample Bank",
        ticker="SAMPLE",
        fundamental=fundamental,
        technical=technical,
        news=news,
    )

    assert result.visual_summary is not None
    assert result.visual_summary.stance == describe_rating_stance(result.final_rating)
    assert result.visual_summary.component_contributions[0].name == "fundamental"
    assert "Revenue growth remains healthy." in result.visual_summary.top_positives
    assert "Provisioning could rise." in result.visual_summary.top_risks
