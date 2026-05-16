# FastAPI Company and Document Ingestion Slice

## Goal

Expose the first production-facing FastAPI backend APIs for company master data and document injection, then wire the existing frontend company and document screens to those APIs.

## Implementation Notes

- Add FastAPI app, route schemas, CORS, and a dev entrypoint.
- Persist companies, document upload rows, and ingestion status in PostgreSQL.
- Store uploaded files under local `uploads/documents/` for the first slice.
- Run document ingestion asynchronously through FastAPI `BackgroundTasks`.
- Sync ingestion stage, page count, processed pages, chunk count, vector IDs, report rows, and failures back to the document row.
- Keep workflow and supervisor-run transport mock-driven until their API contracts are implemented. The follow-up chat screen now has its own backend contract and should no longer use a mock reply path.

## Verification

- Run focused Python route and ingestion-service tests.
- Run the frontend lint/build checks after replacing localStorage state with API calls.
- Commit only the scoped backend/API/frontend integration changes and leave unrelated notebook edits untouched.
