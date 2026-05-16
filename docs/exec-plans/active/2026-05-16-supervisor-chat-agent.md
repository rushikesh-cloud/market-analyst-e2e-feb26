# Supervisor Chat Agent

## Goal

Add a second supervisor layer for interactive follow-up questions. The static supervisor remains the complete company-analysis workflow. The chat supervisor wraps the existing worker agents as tools so user questions can be routed to the right evidence source on demand.

## Scope

- Add typed chat context, request, message, and response contracts.
- Add a `services.supervisor_chat` module that builds a LangChain `create_agent` supervisor with fundamental, technical, and news worker tools.
- Keep short-term memory caller-owned and bounded through message history passed into each chat turn.
- Preserve technical ticker semantics for provider-specific tickers such as `.NS`; the fundamental worker still owns RAG ticker normalization internally.
- Update docs/specs and focused tests for chat routing and history behavior.

## Verification

- Run focused supervisor-chat tests.
- Run the full pytest suite.
