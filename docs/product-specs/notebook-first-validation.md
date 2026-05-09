# Notebook-First Validation Spec

## Purpose

Before building the API backend, the project will validate the complete market analysis workflow through Jupyter notebooks. Each notebook should show the capability in action while importing reusable logic from structured Python modules that can later be used by the FastAPI service layer.

The notebooks are not the system architecture. They are executable validation surfaces for the architecture.

## Notebook Inventory

Create the notebooks in this order:

| Order | Notebook | Goal | Reusable module surface |
| --- | --- | --- | --- |
| 00 | `00_environment_smoke.ipynb` | Validate environment variables, Azure OpenAI connectivity, database connectivity, and local imports. | `config`, `providers`, `telemetry` |
| 01 | `01_data_ingestion.ipynb` | Load company inputs, ticker metadata, market data, and run-level configuration into typed objects. | `types`, `services.ingestion` |
| 02 | `02_document_loading.ipynb` | Load annual reports and PDFs, extract pages/tables/text, and normalize document records. | `providers.document_intelligence`, `services.document_loading` |
| 03 | `03_rag_pipeline.ipynb` | Chunk document text, build full-text search vectors, embed it, store it, and retrieve context with hybrid search. | `repositories`, `services.rag` |
| 04 | `04_fundamental_agent.ipynb` | Use RAG context to produce growth, debt, cash-flow, and risk analysis. | `services.agents.fundamental` |
| 05 | `05_technical_agent.ipynb` | Pull price history, generate indicators/charts, and produce technical analysis. | `services.agents.technical` |
| 06 | `06_news_agent.ipynb` | Pull current news, summarize events, and score sentiment. | `services.agents.news` |
| 07 | `07_supervisor_agent.ipynb` | Combine fundamental, technical, and news outputs into a final market view. | `runtime.graph`, `services.supervisor` |
| 08 | `08_end_to_end_validation.ipynb` | Run a complete sample company workflow and capture outputs for backend parity tests. | all reusable surfaces |

## Notebook Principles

- Keep notebooks thin: orchestration, visual inspection, temporary experiments, and result display belong in cells.
- Keep reusable behavior in importable modules: parsing, validation, provider calls, database access, retrieval, scoring, graph state, and agent prompts belong outside notebooks.
- Each notebook must start with a small setup cell that imports project modules and validates required settings.
- Each notebook must end with a deterministic validation cell that asserts the minimum successful output shape.
- Intermediate data frames, charts, retrieved chunks, and agent traces should be displayed so the workflow can be inspected quickly.
- Any notebook-only experiment that becomes useful twice should be promoted into a reusable module before backend work begins.
- The RAG notebook must display full-text search results, vector search results, and the final fused hybrid results separately.

## Acceptance Criteria

- All notebooks can run independently after environment setup.
- Notebooks import shared logic from project modules instead of duplicating core implementation.
- Each notebook produces a clear visible artifact, such as extracted pages, chunk samples, retrieval results, charts, agent JSON, or supervisor report.
- Shared modules follow the dependency order: Types -> Config -> Repo -> Service -> Runtime -> UI.
- The final end-to-end notebook output can be used as a parity fixture for the first API implementation.

## Out of Scope For This Phase

- FastAPI route implementation.
- React UI implementation.
- Production job scheduling.
- Full authentication and user management.
- Non-notebook deployment automation.
