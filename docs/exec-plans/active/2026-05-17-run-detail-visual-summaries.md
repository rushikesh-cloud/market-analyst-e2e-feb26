# Run Detail Visual Summaries

## Goal

Replace the current long-scroll run-detail page with a summary-first analyst workspace backed by structured worker payloads that expose compact metrics, stance labels, risks, and watch items for direct UI rendering.

## Scope

- Extend the fundamental, technical, news, and supervisor result shapes with normalized visual-summary fields.
- Persist the richer worker and supervisor payloads on supervisor runs without changing the database table shape.
- Update the FastAPI supervisor-run response schema to expose the richer nested payloads needed by the frontend.
- Refactor the run-detail page into a compact summary header plus tab-based overview, fundamental, technical, and news views.
- Keep the chat rail and technical chart support intact while reducing explanatory filler text and generic detail cards.

## Verification

- Run focused backend tests for supervisor-run serialization or route responses impacted by the richer payload shapes.
- Run frontend lint after replacing the stacked run-detail panels with the tabbed workspace.
- Smoke-check that queued, running, completed, and failed runs still render safely when the new structured fields are partially missing.
