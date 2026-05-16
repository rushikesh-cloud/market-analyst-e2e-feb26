from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from market_analyst.config.settings import Settings
from market_analyst.services import document_ingestion
from market_analyst.types.documents import MarkdownReport, ReportInput


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


def test_document_ingestion_persists_stage_transitions(monkeypatch, tmp_path) -> None:
    source_path = tmp_path / "annual-report.pdf"
    source_path.write_bytes(b"pdf")
    settings = _settings(tmp_path)
    transitions: list[dict[str, object]] = []

    monkeypatch.setattr(
        document_ingestion,
        "get_document",
        lambda passed_settings, document_id: {
            "id": document_id,
            "company_id": "company-1",
            "source_path": str(source_path),
        },
    )
    monkeypatch.setattr(
        document_ingestion,
        "get_company",
        lambda passed_settings, company_id: {
            "id": company_id,
            "name": "Reliance Industries",
            "ticker": "RELIANCE",
        },
    )

    def fake_update(passed_settings, document_id, **kwargs):
        transitions.append(kwargs)
        return {}

    monkeypatch.setattr(document_ingestion, "update_document_status", fake_update)
    monkeypatch.setattr(
        document_ingestion,
        "load_report_as_markdown",
        lambda report: MarkdownReport(
            report=ReportInput(path=source_path, company_name="Reliance Industries", ticker="RELIANCE"),
            markdown="# Reliance\n\ncontent",
            page_count=3,
        ),
    )
    monkeypatch.setattr(
        document_ingestion,
        "split_markdown_report",
        lambda markdown_report: [
            Document(page_content="chunk 1", metadata={"source_path": str(source_path), "ticker": "RELIANCE"}),
            Document(page_content="chunk 2", metadata={"source_path": str(source_path), "ticker": "RELIANCE"}),
        ],
    )
    monkeypatch.setattr(document_ingestion, "build_embeddings", lambda passed_settings: object())
    monkeypatch.setattr(document_ingestion, "build_vector_store", lambda passed_settings, embeddings, reset_collection: object())
    monkeypatch.setattr(document_ingestion, "add_chunks_to_vector_store", lambda vector_store, chunks: ["a", "b"])
    monkeypatch.setattr(
        document_ingestion,
        "sync_chunks_to_project_tables",
        lambda passed_settings, chunks, replace_source, document_id: 2,
    )

    document_ingestion.run_document_ingestion(settings, "document-1")

    assert [item["stage"] for item in transitions] == [
        "extracting_markdown",
        "chunking",
        "embedding",
        "syncing_reports",
        "completed",
    ]
    assert transitions[1]["page_count"] == 3
    assert transitions[2]["chunk_count"] == 2
    assert transitions[3]["vector_ids_count"] == 2
    assert transitions[4]["reports_rows"] == 2
