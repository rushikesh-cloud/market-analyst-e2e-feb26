# specs.md: Multi-Agent Market Analysis Engine

## 1. Project Overview

A full-stack, multi-agent system designed to provide 360-degree market intelligence by synthesizing fundamental, technical, and news-based data. The system uses a supervisor-worker architecture to generate high-conviction investment signals.

## 2. Technical Stack

* **Frontend:** React.js (Next.js preferred), Tailwind CSS, Lucide Icons.
* **Backend:** Python 3.11+, FastAPI.
* **Orchestration:** LangChain v0.1 (Agent Objects) + LangGraph (Stateful Workflows).
* **LLMs:** Azure OpenAI (GPT-4o for complex reasoning, GPT-4o-mini for vision/summarization).
* **Database:** PostgreSQL with `pgvector` for Hybrid Search (Vector + Full-Text).
* **Tools:**
* **Fundamental:** Azure AI Document Intelligence.
* **Technical:** `yfinance` + Plotly/Matplotlib.
* **News:** Tavily Search API.



---

## 3. System Architecture

### 3.1. The Multi-Agent Graph (LangGraph)

The system follows a **Supervisor-Worker** pattern. The Supervisor orchestrates three specialized workers:

1. **Fundamental Agent:**
* **Input:** Company Name + Uploaded PDF. If a market-data ticker includes an exchange suffix such as `.NS`, the fundamental RAG comparison strips the suffix and uses the base ticker for report matching.
* **Processing:** Uses Azure AI Document Intelligence `prebuilt-layout` markdown extraction -> splits by markdown header levels -> preserves complete tables as atomic chunks with nearby text context -> applies size-aware chunk refinement to non-table text -> stores chunks and embeddings in Postgres/pgvector.
* **Tool:** RAG (Hybrid Search) to analyze growth, debt, and cash flow.
* **Output:** Fundamental Rating (1-100, where 100 is most positive) + Rationale.


2. **Technical Agent:**
* **Input:** Ticker Symbol. The technical agent preserves the ticker exactly as supplied so provider-specific symbols such as Indian `ticker.NS` values continue to work with `yfinance`.
* **Processing:** Pulls data from `yfinance` -> Generates technical charts with moving averages, RSI, and MACD -> Saves the chart as an image artifact.
* **Tool:** Multi-modal Azure OpenAI chat model to inspect the chart image and identify trend, momentum, support/resistance, breakout/breakdown risk, and a technical rating.
* **Output:** Technical Rating (1-100, where 100 is most positive) + Trend Analysis.


3. **News Agent:**
* **Input:** Company Name + Ticker.
* **Tool:** Tavily Search API through the `langchain-tavily` LangChain tool.
* **Processing:** Runs recent company/ticker news search plus sector-context search, separates favorable and adverse developments, identifies stock implications and watch items, and returns source-attributed JSON.
* **Output:** News Rating (1-100, where 100 is most positive), positive/negative news bullets, sector context, stock implications, watch items, and source links.


4. **Supervisor Agent:**
* **Role:** Aggregates outputs from the three workers.
* **Logic:** Weighs worker ratings to provide a final "Projected Future Performance" report.
* **Output:** Final Future-Perspective Rating (1-100, where 100 is most positive) with component rating rationale.



---

## 4. Data Strategy & Schema

### 4.1. Hybrid Search (Postgres)

We implement Hybrid Search using **Reciprocal Rank Fusion (RRF)** to combine:

* **Vector Search:** Semantic meaning (e.g., "What is the management's view on risk?").
* **Full-Text Search:** Keyword precision (e.g., searching for specific fiscal years like "2024").

### 4.2. Database Schema (Entities)

* **`Companies`:** ID, Ticker, Name, Overall_Score, Status (Processing/Completed).
* **`Reports`:** Company_ID, Content (Full Text), Search_Vector (`tsvector`), Embedding (Vector), Page_Number, Metadata.
* **`Analysis_Results`:** Company_ID, Fundamental_JSON, Technical_JSON, News_JSON, Supervisor_Summary.

---

## 5. Module Breakdown

### 5.0. Notebook-First Validation

Before the backend API is implemented, the system will be validated through Jupyter notebooks. These notebooks are the first executable surface for data ingestion, document loading, RAG, the three worker agents, and the supervisor agent.

The notebooks must stay thin. Reusable behavior must live in structured Python modules that can later be imported by the FastAPI backend without reimplementation. Notebook cells should focus on orchestration, visual inspection, quick experiments, and validation output. The first runnable agent notebook uses LangChain `create_agent` from a shared service module so the notebook validates the same object shape that later runtime code can reuse. The end-to-end RAG agent notebook must demonstrate document selection, Azure Document Intelligence extraction, table-aware chunk inspection, vector DB persistence, full-text/vector/hybrid retrieval, and agentic fundamentals Q&A in one flow.

Required notebooks:

1. `00_environment_smoke.ipynb`
2. `01_data_ingestion.ipynb`
3. `02_document_loading.ipynb`
4. `03_rag_pipeline.ipynb`
5. `04_fundamental_agent.ipynb`
6. `05_technical_agent.ipynb`
7. `06_news_agent.ipynb`
8. `07_supervisor_agent.ipynb`
9. `08_end_to_end_validation.ipynb`

Current companion notebook:

- `04_rag_agent_end_to_end.ipynb`: runnable document-to-RAG-agent validation path for fundamentals questions before the dedicated worker-agent notebooks are fully split out.

Notebook-specific requirements and acceptance criteria are defined in `docs/product-specs/notebook-first-validation.md`. Reusable module boundaries for this phase are defined in `docs/design-docs/notebook-first-modularization.md`.

### 5.1. Backend (Python/LangGraph)

* **State Management:** The `AgentState` object will pass the ticker, the paths to generated charts, and the retrieved RAG contexts between nodes.
* **Batch Processing:** Uses Python's `asyncio` to trigger the three agents in parallel within the LangGraph.

### 5.2. Frontend (React)

* **Workflow Page:** A one-user SaaS workspace lists every stock-analysis workflow with company name, ticker, run status, final supervisor rating, last updated time, and compact status indicators for the fundamental, technical, and news agents.
* **New Workflow Flow:** A minimal stock form captures company name, ticker, optional sector, and a report/PDF placeholder. Submitting the form starts a supervisor workflow and routes the user into the run detail view.
* **Run Detail Page:** The run detail view exposes the supervisor timeline, fixed initial prompt stage, fundamental agent stream, technical chart/analysis stream, news analysis stream, and final supervisor outcome.
* **Streaming Adapter:** The first frontend scaffold uses mock streaming events with the same conceptual shape expected from the future backend: run started, agent started, agent chunk, chart ready, agent completed, supervisor started, supervisor chunk, supervisor completed, and error.
* **Chat Pod:** A dedicated chat window is scoped to one completed stock run. Follow-up questions are answered by the supervisor against the existing worker outputs and stored workflow context.
* **Integration Path:** The mock stream adapter will later be replaced by FastAPI streaming transport without rewriting the visual workflow, timeline, agent panels, supervisor panel, or chat pod.

---

## 6. Implementation Milestones

1. **Phase 0:** Notebook-first validation and reusable module scaffolding.
2. **Phase 1:** Document Ingestion Pipeline (Azure Document Intelligence Markdown -> Header Chunks -> Postgres Hybrid Search).
3. **Phase 2:** Technical Chart Generator + Multi-modal Vision Agent.
4. **Phase 3:** News Crawler & Sentiment Integration via Tavily and LangChain `create_agent`.
5. **Phase 4:** LangGraph Supervisor logic and Scoring weights.
6. **Phase 5:** FastAPI backend integration using the notebook-validated reusable modules.
7. **Phase 6:** React UI & streaming workflow integration. The first scaffold is a clickable Next.js/Tailwind/Lucide frontend with mock streaming data; backend integration follows after API contracts are finalized.
