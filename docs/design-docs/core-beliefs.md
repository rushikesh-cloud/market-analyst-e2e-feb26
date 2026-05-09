# Core Beliefs

## Notebook First, Backend Ready

The first working surface should be Jupyter notebooks because they make data, retrieval, agent behavior, charts, and scoring visible. The notebooks should not become a second implementation. Durable behavior must move into reusable Python modules as soon as it is stable enough to be shared.

## Typed Boundaries

Data entering the system must be validated at the boundary where it appears: company inputs, document extraction output, market data, retrieved chunks, agent responses, and supervisor summaries. Avoid inferred shapes in notebook cells.

## Provider Isolation

External services such as Azure OpenAI, Azure AI Document Intelligence, Tavily, `yfinance`, and PostgreSQL must be injected through provider interfaces or explicit configuration. Notebooks may demonstrate provider calls, but they should not own provider construction details beyond setup and selection.

## Observable Execution

Notebook runs should expose enough state to debug the workflow: input identifiers, document counts, chunk counts, retrieval scores, chart generation paths, agent timing, and final score components.

## Parity With The API

The backend API should reuse the same modules demonstrated in notebooks. The end-to-end notebook should become the reference workflow for API parity tests.
