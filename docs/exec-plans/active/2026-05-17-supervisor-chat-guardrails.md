# Supervisor Chat Guardrails

## Goal

Add explicit guardrails to supervisor chat so it only answers market-related follow-up questions within the current product scope: fundamentals, technicals, news, and the existing supervisor view.

## Scope

- Reject out-of-scope chat prompts before the LLM/tool layer runs.
- Keep allowed follow-ups focused on market, stock, fundamentals, technicals, news, and supervisor-rating questions.
- Prepend a standard cautionary note whenever the user asks for a future-looking recommendation or prediction.
- Add LangChain input middleware for prompt-injection and jailbreak detection before normal agent execution.
- Attach Azure Prompt Shield middleware when the optional package and Azure AI project-endpoint configuration are available.
- Update `specs.md` and focused tests for the new guardrail behavior.

## Verification

- Run focused supervisor-chat and API tests.
