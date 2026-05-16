# Supervisor Agent Ratings

## Goal

Finalize the notebook-first supervisor service so fundamental, technical, and news worker agents each expose a 1-100 rating, and the supervisor aggregates those worker ratings into a final stock future-perspective rating.

## Scope

- Add typed contracts for the RAG-based fundamental worker and supervisor output.
- Normalize model/provider score output to the 1-100 rating contract.
- Keep existing news sentiment-score compatibility while introducing the common `rating` field.
- Add deterministic supervisor aggregation with configurable worker weights.
- Update specs and focused tests for the rating contract.

## Verification

- Run focused pytest coverage for scoring, worker prompt contracts, and supervisor aggregation.
- Run the full test suite if focused tests pass.
