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
* **Input:** Company Name + Uploaded PDF.
* **Processing:** Uses Azure Doc AI to extract tables/text -> Chunks -> Stores in Postgres.
* **Tool:** RAG (Hybrid Search) to analyze growth, debt, and cash flow.
* **Output:** Fundamental Score (0-100) + Rationale.


2. **Technical Agent:**
* **Input:** Ticker Symbol.
* **Processing:** Pulls data from `yfinance` -> Generates OHLC charts with indicators (RSI, MACD) -> Converts to Image.
* **Tool:** Multi-modal LLM (GPT-4o-mini) to "see" the chart and identify patterns (Support/Resistance, Breakouts).
* **Output:** Technical Score (0-100) + Trend Analysis.


3. **News Agent:**
* **Input:** Company Name + Ticker.
* **Tool:** Tavily Search.
* **Processing:** Scrapes latest headlines -> Sentiment Analysis.
* **Output:** Sentiment Score (0-100) + Recent News Bulletins.


4. **Supervisor Agent:**
* **Role:** Aggregates outputs from the three workers.
* **Logic:** Weighs scores to provide a final "Projected Future Performance" report.



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

The notebooks must stay thin. Reusable behavior must live in structured Python modules that can later be imported by the FastAPI backend without reimplementation. Notebook cells should focus on orchestration, visual inspection, quick experiments, and validation output.

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

Notebook-specific requirements and acceptance criteria are defined in `docs/product-specs/notebook-first-validation.md`. Reusable module boundaries for this phase are defined in `docs/design-docs/notebook-first-modularization.md`.

### 5.1. Backend (Python/LangGraph)

* **State Management:** The `AgentState` object will pass the ticker, the paths to generated charts, and the retrieved RAG contexts between nodes.
* **Batch Processing:** Uses Python's `asyncio` to trigger the three agents in parallel within the LangGraph.

### 5.2. Frontend (React)

* **Dashboard:** High-level view of all companies analyzed.
* **Polling Logic:** A `useInterval` hook (5s) checks the `/status/{ticker}` endpoint.
* **Chat Pod:** A dedicated chat window for each company. The frontend sends the user query to the Supervisor Agent, which has the context of the entire graph's output and the Postgres DB.

---

## 6. Implementation Milestones

1. **Phase 0:** Notebook-first validation and reusable module scaffolding.
2. **Phase 1:** Document Ingestion Pipeline (Azure Doc AI -> Postgres Hybrid Search).
3. **Phase 2:** Technical Chart Generator + Multi-modal Vision Agent.
4. **Phase 3:** News Crawler & Sentiment Integration via Tavily.
5. **Phase 4:** LangGraph Supervisor logic and Scoring weights.
6. **Phase 5:** FastAPI backend integration using the notebook-validated reusable modules.
7. **Phase 6:** React UI & Real-time Polling Integration.
