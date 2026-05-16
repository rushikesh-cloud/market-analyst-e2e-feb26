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
            "document_name": "annual-report.pdf",
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


def test_document_ingestion_stage_history_advances_cleanly() -> None:
    from market_analyst.repositories.documents import _advance_stage_history

    history = [
        {
            "stage": "stored",
            "status": "completed",
            "started_at": "2026-05-16T12:00:00+00:00",
            "completed_at": "2026-05-16T12:00:00+00:00",
        }
    ]

    history = _advance_stage_history(history, stage="extracting_markdown", lifecycle_status="processing")
    history = _advance_stage_history(history, stage="chunking", lifecycle_status="processing")
    history = _advance_stage_history(history, stage="embedding", lifecycle_status="processing")
    history = _advance_stage_history(history, stage="syncing_reports", lifecycle_status="processing")
    history = _advance_stage_history(history, stage="completed", lifecycle_status="completed")

    by_stage = {entry["stage"]: entry for entry in history}

    assert by_stage["stored"]["status"] == "completed"
    assert by_stage["extracting_markdown"]["status"] == "completed"
    assert by_stage["chunking"]["status"] == "completed"
    assert by_stage["embedding"]["status"] == "completed"
    assert by_stage["syncing_reports"]["status"] == "completed"
    assert by_stage["completed"]["status"] == "completed"
    assert by_stage["completed"]["completed_at"] is not None
