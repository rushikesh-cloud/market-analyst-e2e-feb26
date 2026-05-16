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
* **Input:** Company Name + Uploaded PDF + the company's normal/internal ticker for report matching. If a market-data ticker includes an exchange suffix such as `.NS`, the fundamental RAG comparison strips the suffix and uses the base ticker for report matching.
* **Processing:** Uses Azure AI Document Intelligence `prebuilt-layout` markdown extraction -> splits by markdown header levels -> preserves complete tables as atomic chunks with nearby text context -> applies size-aware chunk refinement to non-table text -> stores chunks and embeddings in Postgres/pgvector.
* **Tool:** RAG (Hybrid Search) to analyze growth, debt, and cash flow.
* **Output:** Fundamental Rating (1-100, where 100 is most positive) + Rationale.


2. **Technical Agent:**
* **Input:** Yahoo Finance ticker symbol. The technical agent preserves the ticker exactly as supplied so provider-specific symbols such as Indian `ticker.NS` values continue to work with `yfinance`.
* **Processing:** Pulls data from `yfinance` -> Generates technical charts with moving averages, RSI, and MACD -> Saves the chart as an image artifact.
* **Tool:** Multi-modal Azure OpenAI chat model to inspect the chart image and identify trend, momentum, support/resistance, breakout/breakdown risk, and a technical rating.
* **Output:** Technical Rating (1-100, where 100 is most positive) + Trend Analysis.

   Parallel validation path:
* **Technical Agent V2:** A separate LangChain `create_agent` worker remains isolated from V1 until replacement time.
* **Input:** Ticker Symbol plus dynamic duration/period, candle interval, and per-indicator configurations.
* **Processing:** Uses tool-calling to fetch price history, generate candlestick charts on demand, attach only the requested indicator panels and overlays, and then run multimodal chart analysis against the generated image.
* **Supported indicators for the first V2 slice:** MACD, RSI, and Bollinger Bands with user-configurable parameters.
* **Output:** Technical Rating (1-100), structured chart-summary evidence, and the generated chart artifact path.


3. **News Agent:**
* **Input:** Company Name + Ticker.
* **Tool:** Tavily Search API through the `langchain-tavily` LangChain tool.
* **Processing:** Runs recent company/ticker news search plus sector-context search, separates favorable and adverse developments, identifies stock implications and watch items, and returns source-attributed JSON.
* **Output:** News Rating (1-100, where 100 is most positive), positive/negative news bullets, sector context, stock implications, watch items, and source links.


4. **Supervisor Agent:**
* **Role:** Aggregates outputs from the three workers.
* **Logic:** Weighs worker ratings to provide a final "Projected Future Performance" report.
* **Output:** Final Future-Perspective Rating (1-100, where 100 is most positive) with component rating rationale.


5. **Supervisor Chat Agent:**
* **Role:** Answers follow-up questions after or alongside a supervisor run.
* **Logic:** Runs as a second supervisor layer with the fundamental, technical, and news worker agents attached as tools. It routes user questions to the right worker tool when the question needs fresh fundamental, technical, or news evidence, and uses the attached supervisor snapshot for questions about the existing overall rating.
* **State:** Maintains bounded short-term chat history supplied by the caller for continuous follow-up turns. Long-term persistence remains a later backend concern.
* **Output:** Conversational answer grounded in the supervisor snapshot and any worker-tool results used during the turn.



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
- `05_technical_agent_v2.ipynb`: separate technical-agent V2 validation path for dynamic indicator-driven charts built through LangChain `create_agent` tools without replacing V1 yet.

Notebook-specific requirements and acceptance criteria are defined in `docs/product-specs/notebook-first-validation.md`. Reusable module boundaries for this phase are defined in `docs/design-docs/notebook-first-modularization.md`.

### 5.1. Backend (Python/LangGraph)

* **State Management:** The `AgentState` object will pass the ticker, the paths to generated charts, and the retrieved RAG contexts between nodes.
* **Batch Processing:** Uses Python's `asyncio` to trigger the three agents in parallel within the LangGraph.
* **Chat Engine:** A separate chat-facing supervisor agent exposes the three worker agents as callable tools and accepts bounded short-term message history for continuous follow-up questions.
* **Technical V2 Evaluation Surface:** The dynamic technical-agent V2 stays as a separate service/notebook path until it reaches parity and is explicitly promoted to replace V1.
* **FastAPI Company API:** The first backend integration slice exposes company creation, listing, and editing through FastAPI. Company creation captures company name, internal ticker, Yahoo Finance ticker, and sector, then persists the normalized company row in PostgreSQL. The edit path allows operators to update every mutable company-master field stored in the row: company name, internal ticker, Yahoo Finance ticker, sector, status, and overall score.
* **FastAPI Document Injection API:** Document upload is asynchronous. The upload request stores the file under local `uploads/documents/`, creates a document row, and schedules ingestion in the background. Each ingestion stage is synced back to PostgreSQL so the frontend can poll status, stage, page count, processed pages, chunk count, vector ID count, report-row count, failure detail, and an ordered per-stage timeline with started/completed timestamps.
* **FastAPI Supervisor Run API:** Supervisor workflows are now persisted backend runs. Creating a run requires selecting an existing company and one completed ingested document that belongs to that company. The API validates the company-document relationship, creates a run row, executes the supervisor workflow in the background, and stores per-agent status plus worker/supervisor JSON on the run row so the frontend can poll workflow history and run detail. During execution, the backend must route the company's normal/internal ticker into the fundamental worker and the company's Yahoo Finance ticker into the technical worker.

### 5.2. Frontend (React)

* **Workflow Page:** A one-user SaaS workspace lists every stock-analysis workflow with company name, ticker, run status, final supervisor rating, last updated time, and compact status indicators for the fundamental, technical, and news agents.
* **Companies Page:** A company-master page lists every defined company with company name, internal ticker, Yahoo Finance ticker, sector, status, overall score, and added timestamp. A plus action opens a compact form for adding company name, ticker, Yahoo Finance ticker, and sector before saving through the FastAPI company API. Each row also exposes an edit action that loads the company into the same form and allows changing all mutable stored fields: company name, internal ticker, Yahoo Finance ticker, sector, status, and overall score.
* **Documents Page:** A document library page lists uploaded documents with document name, company name, file size, upload status, ingestion stage, page/chunk progress, and upload time. Clicking a document row opens a compact floating detail table below that row showing every ingestion stage, whether it is completed/running/upcoming/failed, and the relevant started/completed timestamps. A plus action opens a form where the user selects a company, chooses a document file, submits it to the FastAPI document API, and polls database-backed ingestion status.
* **New Workflow Flow:** The workflow launcher is selection-driven. The user picks an existing company and then one completed document from that company. Submitting the form creates a persisted supervisor run through FastAPI and routes the user into the run detail view for that backend run.
* **Run Detail Page:** The run detail view exposes the supervisor timeline, selected document context, vertically stacked collapsible fundamental, technical, and news agent outputs, and the final supervisor outcome. The first backend-connected slice polls persisted run state rather than streaming tokens live.
  On newly created or still-running backend runs, agent panels must not show mock evidence, placeholder cards, or seeded analysis copy; until a persisted worker result exists, the body stays blank apart from minimal waiting-state text. When a worker answer is stored as a JSON string, the UI must parse and render that payload as structured evidence/details instead of showing the raw JSON blob in the panel body. The technical panel must render the actual generated chart image used for analysis inside the block itself. The fundamental panel must render a compiled source-page list for the annual-report chunks used to ground the answer, and the news panel must render the source website list returned by the news worker.
* **Agents Page:** The previous hash-linked agents block is now a proper Next.js page that documents the backend-connected agent surfaces.
* **Streaming Adapter:** The early frontend scaffold used mock streaming events with the same conceptual shape expected from the future backend. The current backend-connected workflow pages now poll persisted supervisor runs while live streaming remains a later transport enhancement.
* **Chat Pod:** A dedicated chat window is scoped to one completed stock run. Follow-up questions are answered by the supervisor against the existing worker outputs and stored workflow context through a FastAPI chat turn endpoint backed by the existing supervisor chat service. Before supervisor completion, the chat pod must stay visually empty aside from a disabled-state message and must not display mock "result ready" content. On desktop run-detail layouts, the chat pod stays pinned on the right side while scrolling, its text composer stays anchored to the bottom edge of the pod, and each submitted follow-up must show a visible in-flight assistant placeholder until the backend answer returns.
* **Integration Path:** Company, document, workflow history, run detail pages, and supervisor follow-up chat now use FastAPI transport. The current supervisor run transport is polling-based; future live token streaming can be layered on later without rewriting the visual workflow, timeline, agent panels, supervisor panel, or chat pod.

---

## 6. Implementation Milestones

1. **Phase 0:** Notebook-first validation and reusable module scaffolding.
2. **Phase 1:** Document Ingestion Pipeline (Azure Document Intelligence Markdown -> Header Chunks -> Postgres Hybrid Search).
3. **Phase 2:** Technical Chart Generator + Multi-modal Vision Agent.
4. **Phase 3:** News Crawler & Sentiment Integration via Tavily and LangChain `create_agent`.
5. **Phase 4:** LangGraph Supervisor logic and Scoring weights.
6. **Phase 5:** FastAPI backend integration using the notebook-validated reusable modules.
7. **Phase 6:** React UI & streaming workflow integration. The first scaffold is a clickable Next.js/Tailwind/Lucide frontend with mock streaming data; backend integration follows after API contracts are finalized.
