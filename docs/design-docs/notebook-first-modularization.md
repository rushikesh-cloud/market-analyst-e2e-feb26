# Notebook-First Modularization

## Goal

Use notebooks to validate the workflow while building the reusable Python surfaces that will later power FastAPI and LangGraph runtime execution.

## Proposed Module Boundaries

The reusable package should follow the project dependency order:

```text
market_analyst/
  types/
    company.py
    documents.py
    market_data.py
    analysis.py
    graph_state.py
  config/
    settings.py
  providers/
    azure_openai.py
    document_intelligence.py
    tavily.py
    market_data.py
    database.py
  repositories/
    companies.py
    reports.py
    analysis_results.py
    hybrid_search.py
  services/
    ingestion.py
    document_loading.py
    rag.py
    charting.py
    scoring.py
    agents/
      fundamental.py
      technical.py
      news.py
    supervisor.py
  runtime/
    graph.py
    notebook_runner.py
```

## What Belongs In Notebooks

- Choosing sample companies and input files.
- Displaying extracted pages, tables, chunks, retrieval results, charts, and final reports.
- Running quick experiments and comparing outputs.
- Calling reusable module functions in a readable sequence.
- Capturing validation output for API parity.

## What Belongs In Modules

- Environment parsing and settings validation.
- Provider initialization and API calls.
- Typed request and response models.
- PDF/document extraction normalization.
- Markdown normalization, header-level chunking, embedding, persistence, and hybrid retrieval.
- Market data loading and indicator calculation.
- Prompt construction and agent response parsing.
- Score normalization and supervisor aggregation.
- LangGraph state definitions and graph construction.

## Notebook Setup Contract

Every notebook should use the same setup pattern:

```python
from market_analyst.config.settings import load_settings
from market_analyst.telemetry import configure_notebook_logging

settings = load_settings()
configure_notebook_logging(run_name="notebook-name")
```

If the final module names change during implementation, update this document and the affected notebooks in the same change set.

## Validation Contract

Each notebook should finish with assertions against the expected shape, for example:

```python
assert result.company.ticker
assert result.score >= 0 and result.score <= 100
assert result.rationale
```

The assertions should be lightweight but real. They are the first guardrail before promoting notebook logic into backend tests.
