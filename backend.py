from __future__ import annotations

import argparse
from pathlib import Path

from market_analyst.config.settings import load_settings
from market_analyst.repositories.vector_db import (
    add_chunks_to_vector_store,
    build_embeddings,
    build_vector_store,
    full_text_search,
    hybrid_search,
    sync_chunks_to_project_tables,
    vector_search,
)
from market_analyst.services.rag import build_header_chunks, build_markdown_reports, discover_reports
from market_analyst.types.documents import IngestionResult, ReportInput


def ingest_reports(
    reports_dir: Path | str = "reports",
    reports: list[ReportInput] | None = None,
    max_pages: int | None = None,
    chunk_size: int = 1400,
    chunk_overlap: int = 180,
    persist: bool = True,
    reset_collection: bool = False,
) -> IngestionResult:
    selected_reports = reports or discover_reports(reports_dir)
    markdown_reports = build_markdown_reports(selected_reports, max_pages=max_pages)
    chunks = build_header_chunks(markdown_reports, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    if not persist:
        return IngestionResult(markdown_reports=markdown_reports, chunks=chunks)

    settings = load_settings()
    embeddings = build_embeddings(settings)
    vector_store = build_vector_store(settings, embeddings, reset_collection=reset_collection)
    vector_ids = add_chunks_to_vector_store(vector_store, chunks)
    report_rows = sync_chunks_to_project_tables(settings, chunks, replace_source=True)
    return IngestionResult(
        markdown_reports=markdown_reports,
        chunks=chunks,
        vector_ids=vector_ids,
        reports_rows=report_rows,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest annual reports into the RAG vector database.")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--chunk-size", type=int, default=1400)
    parser.add_argument("--chunk-overlap", type=int, default=180)
    parser.add_argument("--no-persist", action="store_true", help="Only parse markdown and chunks.")
    parser.add_argument("--reset-collection", action="store_true", help="Clear the LangChain vector collection first.")
    args = parser.parse_args()

    result = ingest_reports(
        reports_dir=args.reports_dir,
        max_pages=args.max_pages,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        persist=not args.no_persist,
        reset_collection=args.reset_collection,
    )

    print(f"reports={result.report_count}")
    print(f"chunks={result.chunk_count}")
    print(f"vector_ids={len(result.vector_ids)}")
    print(f"reports_rows={result.reports_rows}")
    for chunk in result.chunks[:5]:
        preview = chunk.page_content.replace("\n", " ")[:180]
        print(f"- {chunk.id} | {chunk.metadata.get('heading_path')} | {preview}")


if __name__ == "__main__":
    main()
