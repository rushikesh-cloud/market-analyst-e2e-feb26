from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from market_analyst.api import dependencies
from market_analyst.api.app import app
from market_analyst.api.routes import companies as companies_route
from market_analyst.api.routes import documents as documents_route
from market_analyst.api.routes import supervisor_runs as supervisor_runs_route
from market_analyst.config.settings import Settings
from market_analyst.types.supervisor_chat import SupervisorChatMessage, SupervisorChatResponse


NOW = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_host="localhost",
        database_port=5432,
        database_name="test",
        database_user="test",
        database_password="test",
        document_intelligence_endpoint="",
        document_intelligence_key="",
        azure_openai_endpoint="",
        azure_openai_key="",
        azure_openai_version="2024-02-01",
        azure_openai_chat_deployment="",
        azure_openai_embedding_deployment="",
        tavily_api_key="",
        upload_dir=tmp_path / "uploads",
    )


def _authenticate() -> dict[str, object]:
    return {
        "id": "auth-user-1",
        "first_name": "Ava",
        "last_name": "Analyst",
        "email": "ava@example.com",
        "mobile_number": "9999999999",
        "gender": "female",
        "dob": NOW.date(),
        "created_at": NOW,
        "updated_at": NOW,
    }


def _company_row() -> dict[str, object]:
    return {
        "id": UUID("0d001055-2737-4c3b-adff-25d1cda5c831"),
        "name": "Reliance Industries",
        "ticker": "RELIANCE",
        "yahoo_finance_ticker": "RELIANCE.NS",
        "sector": "Energy",
        "overall_score": None,
        "status": "pending",
        "created_at": NOW,
        "updated_at": NOW,
    }


def _document_row(source_path: str) -> dict[str, object]:
    return {
        "id": UUID("75961461-d373-4439-9907-a0326e1032ef"),
        "company_id": UUID("0d001055-2737-4c3b-adff-25d1cda5c831"),
        "company_name": "Reliance Industries",
        "document_name": "annual-report.pdf",
        "file_name": "annual-report.pdf",
        "content_type": "application/pdf",
        "file_size": 7,
        "source_path": source_path,
        "status": "uploaded",
        "stage": "stored",
        "page_count": None,
        "pages_processed": None,
        "chunk_count": None,
        "vector_ids_count": None,
        "reports_rows": None,
        "error_message": None,
        "metadata": {},
        "stage_history": [
            {
                "stage": "stored",
                "status": "completed",
                "started_at": NOW.isoformat(),
                "completed_at": NOW.isoformat(),
            }
        ],
        "uploaded_at": NOW,
        "updated_at": NOW,
    }


def _supervisor_run_row() -> dict[str, object]:
    return {
        "id": UUID("351f4fd0-d620-4fb3-9ff0-5449283310cd"),
        "company_id": UUID("0d001055-2737-4c3b-adff-25d1cda5c831"),
        "company_name": "Reliance Industries",
        "ticker": "RELIANCE",
        "yahoo_finance_ticker": "RELIANCE.NS",
        "sector": "Energy",
        "document_id": UUID("75961461-d373-4439-9907-a0326e1032ef"),
        "document_name": "annual-report.pdf",
        "document_status": "completed",
        "status": "queued",
        "error_message": None,
        "final_rating": None,
        "fundamental_status": "idle",
        "technical_status": "idle",
        "news_status": "idle",
        "fundamental_json": None,
        "technical_json": None,
        "news_json": None,
        "supervisor_summary": None,
        "created_at": NOW,
        "updated_at": NOW,
    }


def _completed_supervisor_run_row() -> dict[str, object]:
    row = _supervisor_run_row()
    row["status"] = "completed"
    row["final_rating"] = 74
    row["supervisor"] = {
        "company_name": "Reliance Industries",
        "ticker": "RELIANCE.NS",
        "final_rating": 74,
        "summary": "Overall constructive.",
        "components": [
            {"name": "fundamental", "rating": 80, "weight": 0.45, "rationale": "solid"},
            {"name": "technical", "rating": 72, "weight": 0.30, "rationale": "steady trend"},
            {"name": "news", "rating": 65, "weight": 0.25, "rationale": "mixed sentiment"},
        ],
        "metadata": {"weights": {"fundamental": 0.45, "technical": 0.30, "news": 0.25}},
    }
    return row


def _supervisor_run_with_chart(chart_path: str) -> dict[str, object]:
    row = _supervisor_run_row()
    row["technical"] = {"chart_path": chart_path}
    return row


def test_company_create_and_list_routes(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    app.dependency_overrides[dependencies.require_authenticated_user] = _authenticate
    monkeypatch.setattr(companies_route, "list_companies", lambda passed_settings: [_company_row()])
    monkeypatch.setattr(
        companies_route,
        "create_company",
        lambda passed_settings, **kwargs: {
            **_company_row(),
            "name": kwargs["name"],
            "ticker": kwargs["ticker"].upper(),
            "yahoo_finance_ticker": kwargs["yahoo_finance_ticker"].upper(),
            "sector": kwargs["sector"],
        },
    )

    client = TestClient(app)
    listed = client.get("/api/companies")
    created = client.post(
        "/api/companies",
        json={
            "name": "Reliance Industries",
            "ticker": "reliance",
            "yahooFinanceTicker": "reliance.ns",
            "sector": "Energy",
        },
    )

    app.dependency_overrides.clear()
    assert listed.status_code == 200
    assert listed.json()[0]["ticker"] == "RELIANCE"
    assert created.status_code == 201
    assert created.json()["yahooFinanceTicker"] == "RELIANCE.NS"


def test_document_upload_returns_accepted_status(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    app.dependency_overrides[dependencies.require_authenticated_user] = _authenticate
    monkeypatch.setattr(documents_route, "get_company", lambda passed_settings, company_id: _company_row())
    monkeypatch.setattr(
        documents_route,
        "create_document",
        lambda passed_settings, **kwargs: _document_row(kwargs["source_path"]),
    )
    monkeypatch.setattr(documents_route, "run_document_ingestion", lambda passed_settings, document_id: None)

    client = TestClient(app)
    response = client.post(
        "/api/documents",
        data={"companyId": "company-1"},
        files={"file": ("annual-report.pdf", b"pdfdata", "application/pdf")},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 202
    body = response.json()
    assert body["companyId"] == "0d001055-2737-4c3b-adff-25d1cda5c831"
    assert body["status"] == "uploaded"
    assert body["stage"] == "stored"
    assert body["stageHistory"][0]["stage"] == "stored"
    assert body["stageHistory"][0]["status"] == "completed"
    assert (settings.upload_dir / "company-1").exists()


def test_supervisor_run_create_returns_accepted_status(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    app.dependency_overrides[dependencies.require_authenticated_user] = _authenticate
    monkeypatch.setattr(supervisor_runs_route, "get_company", lambda passed_settings, company_id: _company_row())
    monkeypatch.setattr(
        supervisor_runs_route,
        "get_document",
        lambda passed_settings, document_id: {**_document_row("uploads/company-1/annual-report.pdf"), "status": "completed"},
    )
    monkeypatch.setattr(
        supervisor_runs_route,
        "create_supervisor_run",
        lambda passed_settings, **kwargs: _supervisor_run_row(),
    )
    monkeypatch.setattr(supervisor_runs_route, "execute_supervisor_run", lambda passed_settings, run_id: None)

    client = TestClient(app)
    response = client.post(
        "/api/supervisor-runs",
        json={
            "companyId": "0d001055-2737-4c3b-adff-25d1cda5c831",
            "documentId": "75961461-d373-4439-9907-a0326e1032ef",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 202
    body = response.json()
    assert body["companyId"] == "0d001055-2737-4c3b-adff-25d1cda5c831"
    assert body["documentId"] == "75961461-d373-4439-9907-a0326e1032ef"
    assert body["status"] == "queued"


def test_supervisor_run_create_rejects_document_company_mismatch(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    app.dependency_overrides[dependencies.require_authenticated_user] = _authenticate
    monkeypatch.setattr(supervisor_runs_route, "get_company", lambda passed_settings, company_id: _company_row())
    monkeypatch.setattr(
        supervisor_runs_route,
        "get_document",
        lambda passed_settings, document_id: {**_document_row("uploads/company-2/annual-report.pdf"), "company_id": UUID("11111111-1111-1111-1111-111111111111"), "status": "completed"},
    )

    client = TestClient(app)
    response = client.post(
        "/api/supervisor-runs",
        json={
            "companyId": "0d001055-2737-4c3b-adff-25d1cda5c831",
            "documentId": "75961461-d373-4439-9907-a0326e1032ef",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 409
    assert "Document does not belong" in response.text


def test_supervisor_run_chart_route_returns_file(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    app.dependency_overrides[dependencies.require_authenticated_user] = _authenticate
    chart_path = tmp_path / "chart.png"
    chart_path.write_bytes(b"png")
    monkeypatch.setattr(supervisor_runs_route, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        supervisor_runs_route,
        "get_supervisor_run",
        lambda passed_settings, run_id: _supervisor_run_with_chart(str(chart_path)),
    )

    client = TestClient(app)
    response = client.get("/api/supervisor-runs/351f4fd0-d620-4fb3-9ff0-5449283310cd/technical-chart")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.content == b"png"


def test_supervisor_run_chat_returns_answer_and_history(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    app.dependency_overrides[dependencies.require_authenticated_user] = _authenticate
    monkeypatch.setattr(
        supervisor_runs_route,
        "get_supervisor_run",
        lambda passed_settings, run_id: _completed_supervisor_run_row(),
    )

    captured: dict[str, object] = {}

    def fake_chat(settings_arg, request):
        captured["message"] = request.message
        captured["company_name"] = request.context.company_name
        captured["ticker"] = request.context.ticker
        captured["history"] = request.history
        return SupervisorChatResponse(
            answer="Momentum remains constructive.",
            history=[
                SupervisorChatMessage(role="user", content="What changed in technicals?"),
                SupervisorChatMessage(role="assistant", content="Momentum remains constructive."),
            ],
            tool_names=["ask_technical_agent"],
        )

    monkeypatch.setattr(supervisor_runs_route, "run_supervisor_chat_turn", fake_chat)

    client = TestClient(app)
    response = client.post(
        "/api/supervisor-runs/351f4fd0-d620-4fb3-9ff0-5449283310cd/chat",
        json={
            "message": "What changed in technicals?",
            "history": [],
            "maxHistoryMessages": 8,
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["answer"] == "Momentum remains constructive."
    assert response.json()["toolNames"] == ["ask_technical_agent"]
    assert captured["message"] == "What changed in technicals?"
    assert captured["company_name"] == "Reliance Industries"
    assert captured["ticker"] == "RELIANCE.NS"
    assert captured["history"] == []


def test_supervisor_run_chat_requires_completed_run(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    app.dependency_overrides[dependencies.require_authenticated_user] = _authenticate
    monkeypatch.setattr(
        supervisor_runs_route,
        "get_supervisor_run",
        lambda passed_settings, run_id: _supervisor_run_row(),
    )

    client = TestClient(app)
    response = client.post(
        "/api/supervisor-runs/351f4fd0-d620-4fb3-9ff0-5449283310cd/chat",
        json={"message": "What changed?", "history": []},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 409
    assert "available only after the run completes" in response.text
