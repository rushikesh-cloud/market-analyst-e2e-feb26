# Database Schema

Status: initial planning reference. This file should be regenerated or updated when the database models are implemented.

## Planned Entities

### companies

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| ticker | text | Unique market ticker |
| yahoo_finance_ticker | text | Provider-specific ticker for `yfinance`, including exchange suffixes such as `.NS` when needed |
| name | text | Company display name |
| sector | text | Sector classification used by news context and frontend filtering |
| overall_score | numeric | Latest supervisor future-perspective rating from 1 to 100 |
| status | text | Processing state such as `pending`, `processing`, `completed`, or `failed` |
| created_at | timestamptz | Creation timestamp |
| updated_at | timestamptz | Last update timestamp |

### documents

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| company_id | uuid | Foreign key to `companies.id` |
| document_name | text | Uploaded source document display name |
| file_name | text | Stored upload filename |
| content_type | text | Uploaded MIME type when available |
| file_size | bigint | Uploaded file size in bytes |
| source_path | text | Local upload path for the first FastAPI backend slice |
| status | text | Upload/ingestion lifecycle state: `uploaded`, `processing`, `completed`, or `failed` |
| stage | text | Current ingestion stage: `stored`, `extracting_markdown`, `chunking`, `embedding`, `syncing_reports`, `completed`, or `failed` |
| page_count | integer | Total page count when Azure Document Intelligence returns it |
| pages_processed | integer | Number of pages processed when available |
| chunk_count | integer | Number of RAG chunks produced |
| vector_ids_count | integer | Number of chunks written to the LangChain vector store |
| reports_rows | integer | Number of project-level `reports` rows synced |
| error_message | text | Failure detail for failed ingestion jobs |
| metadata | jsonb | Upload metadata such as original filename |
| stage_history | jsonb | Ordered ingestion-stage timeline entries with per-stage status plus `started_at` / `completed_at` timestamps |
| created_at | timestamptz | Upload creation timestamp |
| updated_at | timestamptz | Last status update timestamp |

### reports

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| company_id | uuid | Foreign key to `companies.id` |
| document_id | uuid | Optional foreign key to `documents.id` when produced from an uploaded document |
| document_name | text | Uploaded source document filename or display name |
| source_path | text | Local path or blob URI for the report |
| upload_status | text | Upload lifecycle state such as `uploaded`, `processing`, `completed`, or `failed` |
| content | text | Extracted chunk text |
| search_vector | tsvector | Generated full-text search vector derived from `content` and selected metadata |
| embedding | vector | Reserved for future project-owned semantic retrieval; current ingestion leaves this nullable and stores semantic vectors in LangChain PGVector |
| page_number | integer | Source page number when available |
| metadata | jsonb | Extraction metadata, table references, fiscal year hints, and source details |
| created_at | timestamptz | Creation timestamp |

Current ingestion metadata must include `source_path`, `source_file`, `company_name`, `ticker`, `filing_type`, `chunk_index`, `page_number`, `chunk_id`, and `heading_path`. Header-derived fields may also include `company`, `document`, `page`, and `section`. Table-aware chunks additionally include `contains_table`, `table_index`, `table_format`, `table_char_length`, and `chunk_exceeds_target_size`.

### analysis_results

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| company_id | uuid | Foreign key to `companies.id` |
| document_id | uuid | Foreign key to `documents.id`; identifies the selected document for this supervisor workflow |
| status | text | Run lifecycle state: `queued`, `running`, `completed`, or `failed` |
| error_message | text | Failure detail for failed supervisor runs |
| fundamental_status | text | Fundamental worker state for workflow polling |
| technical_status | text | Technical worker state for workflow polling |
| news_status | text | News worker state for workflow polling |
| fundamental_json | jsonb | Fundamental agent output |
| technical_json | jsonb | Technical agent output |
| news_json | jsonb | News agent output |
| supervisor_summary | jsonb | Final supervisor report, component ratings, and weighting |
| created_at | timestamptz | Creation timestamp |
| updated_at | timestamptz | Last workflow status update timestamp |

### users

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| first_name | text | Registered first name |
| last_name | text | Registered last name |
| email | text | Canonical login email; unique across all auth methods |
| mobile_number | text | Required in the local registration flow |
| gender | text | Required in the local registration flow |
| dob | date | Required in the local registration flow |
| created_at | timestamptz | Creation timestamp |
| updated_at | timestamptz | Last update timestamp |

### auth_identities

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| user_id | uuid | Foreign key to `users.id` |
| provider | text | `local` or `google` |
| provider_subject | text | Local email for `local`; Google subject for `google` |
| email | text | Email associated with this auth identity |
| password_salt | text | Base64 salt for local PBKDF2 credentials; null for Google |
| password_hash | text | Base64 PBKDF2 hash for local credentials; null for Google |
| created_at | timestamptz | Creation timestamp |
| updated_at | timestamptz | Last update timestamp |

One email maps to exactly one user account. When Google sign-in returns a verified email that already exists on a local account, the system auto-links the new Google identity to that existing user instead of creating a duplicate user row.

### user_sessions

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| user_id | uuid | Foreign key to `users.id` |
| token_hash | text | SHA-256 hash of the opaque cookie token |
| expires_at | timestamptz | Session expiry |
| created_at | timestamptz | Session creation timestamp |

## Retrieval Requirement

The RAG pipeline must support hybrid search over `reports.search_vector` and the LangChain PGVector collection, using Reciprocal Rank Fusion to combine full-text and vector rankings.

Full-text search is a first-class schema requirement, not a later enhancement. The implementation should derive `reports.search_vector` from normalized report content and useful structured fields such as ticker, company name, fiscal year, filing type, headings, and page labels when available.

## Planned Indexes

| Table | Index | Purpose |
| --- | --- | --- |
| reports | GIN index on `search_vector` | Keyword and fiscal-year precision for full-text retrieval |
| reports | Vector index on `embedding` | Reserved for future project-owned semantic retrieval |
| reports | B-tree index on `company_id` | Company-scoped retrieval |
| reports | B-tree index on `document_id` | Document-scoped cleanup and API traceability |
| documents | B-tree index on `company_id` | Company-scoped document listing |
| documents | B-tree index on `status` | Polling and operational status views |
| companies | Unique index on `ticker` | Stable company lookup |
| analysis_results | B-tree index on `company_id` | Company-scoped workflow history |
| analysis_results | B-tree index on `document_id` | Document-scoped workflow history |
| analysis_results | B-tree index on `status` | Workflow queue/running/completed filters |
| users | Unique index on `email` | Single operator account per email |
| auth_identities | Unique index on `(provider, provider_subject)` | Stable provider login mapping |
| auth_identities | B-tree index on `user_id` | Fast account-link lookup |
| user_sessions | Unique index on `token_hash` | Session validation |
| user_sessions | B-tree index on `expires_at` | Session cleanup and validation |

## Current LangChain Vector Store

The notebook-first backend writes chunks into LangChain's Postgres vector store collection named `fundamental_report_chunks` by default. This creates LangChain-managed collection and embedding tables alongside the project-level `companies` and `reports` tables.

The project-level `reports` table remains the full-text search and API-parity surface. The LangChain vector store is the current semantic retrieval surface; `reports.embedding` remains nullable until the project needs a project-owned vector index.

## Hybrid Search Contract

Hybrid search should return both component scores before fusion:

- `full_text_rank`: rank or score from PostgreSQL full-text search.
- `vector_distance`: distance from semantic embedding search.
- `rrf_score`: final Reciprocal Rank Fusion score used to order context chunks.

The RAG notebook must show both full-text-only and vector-only results before displaying the fused result set.
