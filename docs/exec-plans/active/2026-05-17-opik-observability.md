# Opik Observability

## Goal

Wire Opik observability into the reusable LangChain/Azure OpenAI runtime surfaces so agent executions and direct chat-model analysis calls emit traces without each caller reimplementing callback setup.

## Scope

- Extend shared settings with the existing `OPIK_*` environment keys already present in `.env`.
- Add a reusable telemetry helper that builds LangChain runnable config plus an `OpikTracer` when Opik is configured.
- Route the current worker-agent invocations and direct multimodal model invocations through that helper.
- Add `@opik.track(...)` decorators to the agent and sub-agent execution functions so Opik captures orchestration-level spans around worker runs and sub-analysis steps.
- Update the working specification and focused tests for the telemetry surface.

## Verification

- Run focused pytest coverage for telemetry and affected agent modules.
- Keep the change scoped to backend/runtime observability and avoid unrelated frontend or notebook edits already in the worktree.
