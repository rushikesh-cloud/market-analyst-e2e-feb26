from market_analyst.config.settings import Settings
from market_analyst import telemetry
from market_analyst.services.agents.fundamental import run_fundamental_analysis_agent
from market_analyst.services.agents.news import run_news_analysis_agent
from market_analyst.services.agents.technical import analyze_technical_chart, run_technical_analysis_agent
from market_analyst.services.agents.technical_v2 import analyze_technical_chart_v2_artifact, run_technical_analysis_agent_v2
from market_analyst.services.supervisor import run_supervisor_agent
from market_analyst.services.supervisor_chat import run_supervisor_chat_turn
from market_analyst.services.supervisor_runs import execute_supervisor_run


def _build_settings(**overrides) -> Settings:
    return Settings(
        database_host="localhost",
        database_port=5432,
        database_name="market",
        database_user="user",
        database_password="password",
        document_intelligence_endpoint="https://example.cognitiveservices.azure.com/",
        document_intelligence_key="document-key",
        azure_openai_endpoint="https://example.openai.azure.com/",
        azure_openai_key="azure-key",
        azure_openai_version="2024-02-01",
        azure_openai_chat_deployment="gpt-4o",
        azure_openai_embedding_deployment="text-embedding-3-large",
        tavily_api_key="tavily-key",
        **overrides,
    )


def test_build_langchain_run_config_adds_opik_callback(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeTracer:
        def __init__(self, *, project_name, tags, metadata):
            captured["project_name"] = project_name
            captured["tags"] = tags
            captured["metadata"] = metadata

    monkeypatch.setattr(telemetry, "OpikTracer", FakeTracer)
    settings = _build_settings(
        opik_api_key="opik-key",
        opik_workspace="MarketAnalyst",
        opik_project_name="market-analyst-dev",
        opik_url_override="https://example.opik/api",
    )

    config = telemetry.build_langchain_run_config(
        settings,
        run_name="fundamental-analysis-agent",
        tags=("agent", "fundamental"),
        metadata={"ticker": "INFY", "document_id": "doc-1"},
    )

    assert config["run_name"] == "fundamental-analysis-agent"
    assert config["tags"] == ["market-analyst", "agent", "fundamental"]
    assert config["metadata"]["application"] == "market-analyst"
    assert config["metadata"]["ticker"] == "INFY"
    assert len(config["callbacks"]) == 1
    assert captured["project_name"] == "market-analyst-dev"
    assert captured["tags"] == ["market-analyst", "agent", "fundamental"]
    assert captured["metadata"]["document_id"] == "doc-1"


def test_build_langchain_run_config_skips_callback_when_opik_disabled(monkeypatch) -> None:
    monkeypatch.setattr(telemetry, "OpikTracer", object)
    settings = _build_settings()

    config = telemetry.build_langchain_run_config(
        settings,
        run_name="news-analysis-agent",
        tags=("agent", "news"),
        metadata={"ticker": "RELIANCE"},
    )

    assert "callbacks" not in config
    assert config["metadata"]["ticker"] == "RELIANCE"


def test_invoke_agent_with_tracing_passes_built_config(monkeypatch) -> None:
    monkeypatch.setattr(
        telemetry,
        "build_langchain_run_config",
        lambda settings, **kwargs: {"run_name": kwargs["run_name"], "tags": list(kwargs["tags"])},
    )
    settings = _build_settings()
    captured: dict[str, object] = {}

    class FakeAgent:
        def invoke(self, payload, config):
            captured["payload"] = payload
            captured["config"] = config
            return {"ok": True}

    result = telemetry.invoke_agent_with_tracing(
        FakeAgent(),
        {"messages": [{"role": "user", "content": "hello"}]},
        settings,
        run_name="supervisor-chat-agent",
        tags=("agent", "supervisor"),
        metadata={"ticker": "TCS"},
    )

    assert result == {"ok": True}
    assert captured["config"] == {
        "run_name": "supervisor-chat-agent",
        "tags": ["agent", "supervisor"],
    }


def test_agent_entrypoints_are_opik_tracked() -> None:
    tracked_functions = [
        run_fundamental_analysis_agent,
        run_news_analysis_agent,
        run_technical_analysis_agent,
        analyze_technical_chart,
        run_technical_analysis_agent_v2,
        analyze_technical_chart_v2_artifact,
        run_supervisor_agent,
        run_supervisor_chat_turn,
        execute_supervisor_run,
    ]

    for function in tracked_functions:
        assert hasattr(function, "__wrapped__"), function.__name__
