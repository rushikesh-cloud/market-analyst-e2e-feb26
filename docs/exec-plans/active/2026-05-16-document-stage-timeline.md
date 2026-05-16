# Document Stage Timeline

## Goal

Extend the document-library experience so clicking a document row reveals a compact per-stage timeline with live statuses and timestamps for started/completed ingestion steps.

## Implementation Notes

- Persist ordered document stage-history entries in PostgreSQL alongside the current document row.
- Record timestamps as ingestion advances so completed and active stages can be rendered without frontend guesswork.
- Surface the new history through the FastAPI document schema.
- Render a floating detail table below the selected document row with completed, running, upcoming, and failed stage styling.

## Verification

- Run focused backend tests for the document ingestion service and document API schema/route behavior.
- Run frontend lint/build checks after the row-detail timeline is wired.
- Commit only the scoped document timeline changes.
