# Supervisor Chat API and UI Wiring

## Goal

Connect the run-detail chat pod to the existing supervisor chat service so follow-up questions execute against the backend and show visible in-flight feedback while answers are being generated.

## Scope

- Add a FastAPI supervisor-run chat endpoint that builds chat context from the persisted run.
- Keep short-term chat history caller-owned and round-tripped through the API.
- Replace the frontend mock chat reply path with the real backend call.
- Show a temporary assistant "typing" placeholder while the backend response is pending.

## Verification

- Run focused Python API and supervisor-chat tests.
- Run frontend lint after wiring the chat pod to the backend.
