from market_analyst.services.supervisor import aggregate_supervisor_result, calculate_weighted_rating
from market_analyst.types.fundamental import FundamentalAnalysisResult
from market_analyst.types.news import NewsAnalysisResult
from market_analyst.types.supervisor import SupervisorRatingComponent
from market_analyst.types.technical import TechnicalAnalysisResult


def test_calculate_weighted_rating_renormalizes_available_components() -> None:
    final_rating = calculate_weighted_rating(
        [
            SupervisorRatingComponent("fundamental", 80, 0.5, "solid"),
            SupervisorRatingComponent("technical", None, 0.3, ""),
            SupervisorRatingComponent("news", 60, 0.2, "mixed"),
        ]
    )

    assert final_rating == 74


def test_aggregate_supervisor_result_uses_worker_ratings() -> None:
    result = aggregate_supervisor_result(
        company_name="Sample Bank",
        ticker="SAMPLE",
        fundamental=FundamentalAnalysisResult("Sample Bank", "SAMPLE", "q", "fundamental answer", 90),
        technical=TechnicalAnalysisResult("SAMPLE", "q", "technical answer", 70, chart_path=None, artifact=None),  # type: ignore[arg-type]
        news=NewsAnalysisResult("Sample Bank", "SAMPLE", "Banking", "q", "news answer", rating=50, sentiment_score=50),
    )

    assert result.final_rating == 74
    assert "final future-perspective rating is 74/100" in result.summary
    assert [component.name for component in result.components] == ["fundamental", "technical", "news"]
