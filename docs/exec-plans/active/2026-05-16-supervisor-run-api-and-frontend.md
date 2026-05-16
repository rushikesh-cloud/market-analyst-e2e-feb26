# Supervisor Run API and Frontend Wiring

## Goal

Replace the mock workflow-run creation path with a backend-connected supervisor-run flow that starts from existing companies and completed documents.

## Scope

- Add persisted FastAPI supervisor-run routes for list/get/create.
- Validate company-document ownership and completed document ingestion before run creation.
- Execute the supervisor workflow in the background and persist per-agent state plus worker outputs.
- Replace the hash-based agents block with a real `/agents` page.
- Rewire the workflow list, new workflow panel, and run detail page to use FastAPI instead of mock session state.

## Verification

- Run focused backend route tests for supervisor-run creation and validation.
- Run frontend lint/build after replacing the mock workflow path.
- Leave existing notebook edits untouched and commit only the scoped supervisor-run/frontend integration changes.
