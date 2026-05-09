# Database Schema

Status: initial planning reference. This file should be regenerated or updated when the database models are implemented.

## Planned Entities

### companies

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| ticker | text | Unique market ticker |
| name | text | Company display name |
| overall_score | numeric | Latest supervisor score from 0 to 100 |
| status | text | Processing state such as `pending`, `processing`, `completed`, or `failed` |
| created_at | timestamptz | Creation timestamp |
| updated_at | timestamptz | Last update timestamp |

### reports

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| company_id | uuid | Foreign key to `companies.id` |
| source_path | text | Local path or blob URI for the report |
| content | text | Extracted chunk text |
| search_vector | tsvector | Generated full-text search vector derived from `content` and selected metadata |
| embedding | vector | Embedding for semantic retrieval |
| page_number | integer | Source page number when available |
| metadata | jsonb | Extraction metadata, table references, fiscal year hints, and source details |
| created_at | timestamptz | Creation timestamp |

Current ingestion metadata must include `source_path`, `source_file`, `company_name`, `ticker`, `filing_type`, `chunk_index`, `page_number`, `chunk_id`, and `heading_path`. Header-derived fields may also include `company`, `document`, `page`, and `section`.

### analysis_results

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| company_id | uuid | Foreign key to `companies.id` |
| fundamental_json | jsonb | Fundamental agent output |
| technical_json | jsonb | Technical agent output |
| news_json | jsonb | News agent output |
| supervisor_summary | jsonb | Final supervisor report and score weighting |
| created_at | timestamptz | Creation timestamp |

## Retrieval Requirement

The RAG pipeline must support hybrid search over `reports.search_vector` and `reports.embedding`, using Reciprocal Rank Fusion to combine full-text and vector rankings.

Full-text search is a first-class schema requirement, not a later enhancement. The implementation should derive `reports.search_vector` from normalized report content and useful structured fields such as ticker, company name, fiscal year, filing type, headings, and page labels when available.

## Planned Indexes

| Table | Index | Purpose |
| --- | --- | --- |
| reports | GIN index on `search_vector` | Keyword and fiscal-year precision for full-text retrieval |
| reports | Vector index on `embedding` | Semantic similarity retrieval |
| reports | B-tree index on `company_id` | Company-scoped retrieval |
| companies | Unique index on `ticker` | Stable company lookup |

## Current LangChain Vector Store

The notebook-first backend also writes the same chunks into LangChain's Postgres vector store collection named `fundamental_report_chunks` by default. This creates LangChain-managed collection and embedding tables alongside the project-level `companies` and `reports` tables.

The project-level `reports` table remains the contract for hybrid search and API parity. The LangChain vector store is used for notebook-friendly vector insertion and similarity search while the project schema matures.

## Hybrid Search Contract

Hybrid search should return both component scores before fusion:

- `full_text_rank`: rank or score from PostgreSQL full-text search.
- `vector_distance`: distance from semantic embedding search.
- `rrf_score`: final Reciprocal Rank Fusion score used to order context chunks.

The RAG notebook must show both full-text-only and vector-only results before displaying the fused result set.
