from market_analyst.services import supervisor_chat as supervisor_chat_service
from market_analyst.services.supervisor_chat import (
    append_short_term_history,
    build_supervisor_chat_messages,
    build_supervisor_chat_prompt,
    build_supervisor_chat_tools,
    extract_tool_names,
    summarize_supervisor_snapshot,
)
from market_analyst.types.fundamental import FundamentalAnalysisResult
from market_analyst.types.news import NewsAnalysisResult
from market_analyst.types.supervisor import SupervisorAnalysisResult, SupervisorRatingComponent
from market_analyst.types.supervisor_chat import (
    SupervisorChatContext,
    SupervisorChatMessage,
    SupervisorChatRequest,
)
from market_analyst.types.technical import TechnicalAnalysisResult


def test_build_supervisor_chat_messages_trims_short_term_history() -> None:
    history = [
        SupervisorChatMessage(role="user", content="q1"),
        SupervisorChatMessage(role="assistant", content="a1"),
        SupervisorChatMessage(role="user", content="q2"),
        SupervisorChatMessage(role="assistant", content="a2"),
    ]
    request = SupervisorChatRequest(
        context=SupervisorChatContext(company_name="Reliance", ticker="RELIANCE.NS"),
        message="What changed in the technical view?",
        history=history,
        max_history_messages=2,
    )

    messages = build_supervisor_chat_messages(request)

    assert messages == [
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "What changed in the technical view?"},
    ]


def test_append_short_term_history_keeps_latest_turns() -> None:
    history = [
        SupervisorChatMessage(role="user", content="q1"),
        SupervisorChatMessage(role="assistant", content="a1"),
    ]

    updated = append_short_term_history(
        history=history,
        user_message="q2",
        assistant_answer="a2",
        max_history_messages=3,
    )

    assert updated == [
        SupervisorChatMessage(role="assistant", content="a1"),
        SupervisorChatMessage(role="user", content="q2"),
        SupervisorChatMessage(role="assistant", content="a2"),
    ]


def test_supervisor_chat_tools_route_to_worker_agents(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    def fake_fundamental(settings, request):
        captured["fundamental_question"] = request.question
        captured["fundamental_ticker"] = request.ticker
        return FundamentalAnalysisResult("Reliance", "RELIANCE", request.question, "fundamental answer", 81)

    def fake_technical(settings, request):
        captured["technical_question"] = request.question
        captured["technical_ticker"] = request.ticker
        return TechnicalAnalysisResult(request.ticker, request.question, "technical answer", 62, chart_path=None, artifact=None)  # type: ignore[arg-type]

    def fake_news(settings, request):
        captured["news_question"] = request.question
        captured["news_ticker"] = request.ticker
        captured["news_sector"] = request.sector
        return NewsAnalysisResult("Reliance", request.ticker, request.sector, request.question, "news answer", rating=55)

    monkeypatch.setattr(supervisor_chat_service, "run_fundamental_analysis_agent", fake_fundamental)
    monkeypatch.setattr(supervisor_chat_service, "run_technical_analysis_agent", fake_technical)
    monkeypatch.setattr(supervisor_chat_service, "run_news_analysis_agent", fake_news)

    tools = {
        item.name: item
        for item in build_supervisor_chat_tools(
            settings=None,  # type: ignore[arg-type]
            context=SupervisorChatContext(company_name="Reliance", ticker="RELIANCE.NS", sector="Energy"),
        )
    }

    fundamental_answer = tools["ask_fundamental_agent"].invoke({"question": "How is debt?"})
    technical_answer = tools["ask_technical_agent"].invoke({"question": "How is momentum?"})
    news_answer = tools["ask_news_agent"].invoke({"question": "Any adverse news?"})

    assert "Fundamental worker rating: 81/100" in fundamental_answer
    assert "Technical worker rating: 62/100" in technical_answer
    assert "News worker rating: 55/100" in news_answer
    assert captured["fundamental_ticker"] == "RELIANCE.NS"
    assert captured["technical_ticker"] == "RELIANCE.NS"
    assert captured["news_ticker"] == "RELIANCE.NS"
    assert captured["news_sector"] == "Energy"


def test_supervisor_chat_prompt_includes_static_snapshot() -> None:
    snapshot = SupervisorAnalysisResult(
        company_name="Reliance",
        ticker="RELIANCE.NS",
        final_rating=74,
        summary="Overall constructive.",
        components=[
            SupervisorRatingComponent("fundamental", 80, 0.45, "solid"),
            SupervisorRatingComponent("technical", 70, 0.30, "uptrend"),
            SupervisorRatingComponent("news", 60, 0.25, "mixed"),
        ],
    )
    context = SupervisorChatContext(company_name="Reliance", ticker="RELIANCE.NS", sector="Energy", supervisor_result=snapshot)

    prompt = build_supervisor_chat_prompt(context=context)

    assert "interactive supervisor chat agent" in prompt
    assert "Ticker: RELIANCE.NS" in prompt
    assert "Final rating: 74/100" in summarize_supervisor_snapshot(snapshot)
    assert "Component ratings: fundamental=80, technical=70, news=60" in prompt


def test_extract_tool_names_from_agent_result() -> None:
    names = extract_tool_names(
        {
            "messages": [
                {"tool_calls": [{"name": "ask_fundamental_agent"}, {"name": "ask_news_agent"}]},
            ]
        }
    )

    assert names == ["ask_fundamental_agent", "ask_news_agent"]
