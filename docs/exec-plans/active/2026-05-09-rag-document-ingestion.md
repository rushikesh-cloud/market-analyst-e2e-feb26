# RAG Document Ingestion Plan

## Context

The fundamental analysis path needs a first executable ingestion surface that starts with annual report PDFs, uses Azure Document Intelligence to extract markdown, chunks by markdown headers, and optionally persists the chunks into Postgres/pgvector through LangChain.

## Scope

- Add a reusable backend import surface for report discovery, Azure Document Intelligence markdown extraction, header-level chunking, and vector persistence.
- Keep the notebook thin and focused on orchestration plus chunk inspection.
- Use LangChain components where they fit: Azure Document Intelligence loading, markdown header splitting, table-aware chunk preservation, recursive chunk refinement, Azure OpenAI embeddings, and Postgres vector storage.
- Mirror persisted chunks into the project-level `companies` and `reports` tables for full-text search. Semantic vectors are stored in LangChain PGVector.

## Acceptance Criteria

- `backend.py --no-persist --max-pages 1` produces report and chunk summaries from the local PDFs.
- `notebooks/03_rag_pipeline.ipynb` imports backend modules instead of duplicating ingestion logic.
- The notebook displays markdown previews and header chunk outputs before optional vector DB writes.
- Table chunks preserve complete HTML or markdown tables with bounded before/after text context, even when the resulting table chunk exceeds the nominal chunk target.
- Database writes are opt-in from the notebook and use the existing `.env` database and Azure OpenAI embedding settings.

## Status

Completed for the first notebook-first ingestion slice.
