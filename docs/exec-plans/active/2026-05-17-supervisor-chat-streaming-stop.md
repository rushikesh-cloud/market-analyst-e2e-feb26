# Supervisor Chat Streaming and Stop Control

## Goal

Upgrade the follow-up chat pod from a one-shot backend response to a streamed assistant response with a user-visible stop control.

## Scope

- Add a streaming supervisor-chat API route for completed runs.
- Stream assistant output chunks into the existing chat bubble in the frontend.
- Add a stop control that aborts the active client chat session.
- Keep markdown rendering for streamed/final assistant output.

## Verification

- Run focused supervisor-chat and API tests.
- Run frontend lint after the chat stream consumer and stop control land.
