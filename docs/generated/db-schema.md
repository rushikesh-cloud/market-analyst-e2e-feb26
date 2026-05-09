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
| embedding | vector | Embedding for semantic retrieval |
| page_number | integer | Source page number when available |
| metadata | jsonb | Extraction metadata, table references, fiscal year hints, and source details |
| created_at | timestamptz | Creation timestamp |

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

The RAG pipeline must support hybrid search over `reports.content` and `reports.embedding`, using Reciprocal Rank Fusion to combine full-text and vector rankings.
