from __future__ import annotations

from pathlib import Path

from market_analyst.config.settings import Settings
from market_analyst.repositories.companies import get_company
from market_analyst.repositories.documents import get_document, update_document_status
from market_analyst.repositories.vector_db import (
    add_chunks_to_vector_store,
    build_embeddings,
    build_vector_store,
    sync_chunks_to_project_tables,
)
from market_analyst.services.rag import load_report_as_markdown, split_markdown_report
from market_analyst.types.documents import ReportInput


def run_document_ingestion(settings: Settings, document_id: str) -> None:
    """Run one uploaded document through markdown extraction, chunking, and persistence."""

    try:
        document = get_document(settings, document_id)
        if document is None:
            raise ValueError(f"Document not found: {document_id}")
        company = get_company(settings, str(document["company_id"]))
        if company is None:
            raise ValueError(f"Company not found for document: {document_id}")

        report = ReportInput(
            path=Path(str(document["source_path"])),
            company_name=str(company["name"]),
            ticker=str(company["ticker"]),
        )

        update_document_status(settings, document_id, status="processing", stage="extracting_markdown")
        markdown_report = load_report_as_markdown(report)
        update_document_status(
            settings,
            document_id,
            status="processing",
            stage="chunking",
            page_count=markdown_report.page_count,
            pages_processed=markdown_report.page_count,
        )

        chunks = split_markdown_report(markdown_report)
        update_document_status(
            settings,
            document_id,
            status="processing",
            stage="embedding",
            chunk_count=len(chunks),
        )

        embeddings = build_embeddings(settings)
        vector_store = build_vector_store(settings, embeddings, reset_collection=False)
        vector_ids = add_chunks_to_vector_store(vector_store, chunks)
        update_document_status(
            settings,
            document_id,
            status="processing",
            stage="syncing_reports",
            vector_ids_count=len(vector_ids),
        )

        reports_rows = sync_chunks_to_project_tables(settings, chunks, replace_source=True, document_id=document_id)
        update_document_status(
            settings,
            document_id,
            status="completed",
            stage="completed",
            reports_rows=reports_rows,
        )
    except Exception as exc:
        update_document_status(
            settings,
            document_id,
            status="failed",
            stage="failed",
            error_message=str(exc),
        )
