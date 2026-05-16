from market_analyst.services import supervisor as supervisor_service
from market_analyst.services import supervisor_runs as supervisor_runs_service
from market_analyst.services.supervisor import aggregate_supervisor_result, calculate_weighted_rating, run_supervisor_agent
from market_analyst.types.fundamental import FundamentalAnalysisResult
from market_analyst.types.news import NewsAnalysisResult
from market_analyst.types.supervisor import SupervisorAnalysisRequest
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


def test_supervisor_routes_internal_and_provider_tickers_to_the_right_workers(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    def fake_fundamental(settings, request):
        captured["fundamental_ticker"] = request.ticker
        return FundamentalAnalysisResult("Reliance", "RELIANCE", "q", "fundamental answer", 80)

    def fake_technical(settings, request):
        captured["technical_ticker"] = request.ticker
        return TechnicalAnalysisResult(request.ticker, "q", "technical answer", 70, chart_path=None, artifact=None)  # type: ignore[arg-type]

    def fake_news(settings, request):
        captured["news_ticker"] = request.ticker
        return NewsAnalysisResult("Reliance", request.ticker, None, "q", "news answer", rating=60, sentiment_score=60)

    monkeypatch.setattr(supervisor_service, "run_fundamental_analysis_agent", fake_fundamental)
    monkeypatch.setattr(supervisor_service, "run_technical_analysis_agent", fake_technical)
    monkeypatch.setattr(supervisor_service, "run_news_analysis_agent", fake_news)

    result = run_supervisor_agent(
        None,  # type: ignore[arg-type]
        SupervisorAnalysisRequest(
            company_name="Reliance",
            ticker="RELIANCE",
            yahoo_finance_ticker="RELIANCE.NS",
        ),
    )

    assert result.final_rating == 72
    assert captured["fundamental_ticker"] == "RELIANCE"
    assert captured["technical_ticker"] == "RELIANCE.NS"
    assert captured["news_ticker"] == "RELIANCE.NS"


def test_execute_supervisor_run_uses_internal_ticker_for_fundamental_and_provider_ticker_for_technical(monkeypatch) -> None:
    captured: dict[str, str | None] = {}
    transitions: list[dict[str, object]] = []

    monkeypatch.setattr(
        supervisor_runs_service,
        "get_supervisor_run",
        lambda settings, run_id: {"id": run_id, "company_id": "company-1", "document_id": "document-1"},
    )
    monkeypatch.setattr(
        supervisor_runs_service,
        "get_company",
        lambda settings, company_id: {
            "id": company_id,
            "name": "Reliance",
            "ticker": "RELIANCE",
            "yahoo_finance_ticker": "RELIANCE.NS",
            "sector": "Energy",
        },
    )
    monkeypatch.setattr(
        supervisor_runs_service,
        "get_document",
        lambda settings, document_id: {"id": document_id},
    )

    def fake_update(settings, run_id, **kwargs):
        transitions.append(kwargs)
        return {"id": run_id, **kwargs}

    def fake_fundamental(settings, request):
        captured["fundamental_ticker"] = request.ticker
        captured["fundamental_document_id"] = request.document_id
        return FundamentalAnalysisResult("Reliance", "RELIANCE", "q", "fundamental answer", 80)

    def fake_technical(settings, request):
        captured["technical_ticker"] = request.ticker
        return TechnicalAnalysisResult(request.ticker, "q", "technical answer", 70, chart_path=None, artifact=None)  # type: ignore[arg-type]

    def fake_news(settings, request):
        captured["news_ticker"] = request.ticker
        return NewsAnalysisResult("Reliance", request.ticker, "Energy", "q", "news answer", rating=60, sentiment_score=60)

    monkeypatch.setattr(supervisor_runs_service, "update_supervisor_run", fake_update)
    monkeypatch.setattr(supervisor_runs_service, "run_fundamental_analysis_agent", fake_fundamental)
    monkeypatch.setattr(supervisor_runs_service, "run_technical_analysis_agent", fake_technical)
    monkeypatch.setattr(supervisor_runs_service, "run_news_analysis_agent", fake_news)
    monkeypatch.setattr(
        supervisor_runs_service,
        "aggregate_supervisor_result",
        lambda **kwargs: supervisor_service.aggregate_supervisor_result(**kwargs),
    )

    supervisor_runs_service.execute_supervisor_run(None, "run-1")  # type: ignore[arg-type]

    assert captured["fundamental_ticker"] == "RELIANCE"
    assert captured["fundamental_document_id"] == "document-1"
    assert captured["technical_ticker"] == "RELIANCE.NS"
    assert captured["news_ticker"] == "RELIANCE.NS"
    assert transitions[-1]["status"] == "completed"
