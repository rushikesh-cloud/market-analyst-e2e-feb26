from __future__ import annotations

from collections.abc import Iterable, Sequence
from uuid import uuid4

import psycopg
from langchain_core.documents import Document
from langchain_openai import AzureOpenAIEmbeddings
from langchain_postgres import PGVector
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from market_analyst.config.settings import Settings


def build_embeddings(settings: Settings) -> AzureOpenAIEmbeddings:
    settings.require_embeddings()
    return AzureOpenAIEmbeddings(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version=settings.azure_openai_version,
        azure_deployment=settings.azure_openai_embedding_deployment,
    )


def build_vector_store(
    settings: Settings,
    embeddings: AzureOpenAIEmbeddings,
    reset_collection: bool = False,
) -> PGVector:
    settings.require_database()
    return PGVector(
        embeddings=embeddings,
        connection=settings.database_url,
        collection_name=settings.vector_collection_name,
        pre_delete_collection=reset_collection,
        use_jsonb=True,
        create_extension=True,
    )


def add_chunks_to_vector_store(
    vector_store: PGVector,
    chunks: Sequence[Document],
) -> list[str]:
    if not chunks:
        return []
    ids = [_document_id(chunk) for chunk in chunks]
    return vector_store.add_documents(documents=list(chunks), ids=ids)


def ensure_project_schema(settings: Settings) -> None:
    settings.require_database()
    with psycopg.connect(settings.psycopg_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    id uuid PRIMARY KEY,
                    ticker text UNIQUE NOT NULL,
                    yahoo_finance_ticker text,
                    name text NOT NULL,
                    sector text,
                    overall_score numeric,
                    status text NOT NULL DEFAULT 'processing',
                    created_at timestamptz NOT NULL DEFAULT now(),
                    updated_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS yahoo_finance_ticker text")
            cur.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS sector text")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id uuid PRIMARY KEY,
                    company_id uuid NOT NULL REFERENCES companies(id),
                    document_name text NOT NULL,
                    file_name text NOT NULL,
                    content_type text,
                    file_size bigint NOT NULL,
                    source_path text NOT NULL,
                    status text NOT NULL DEFAULT 'uploaded',
                    stage text NOT NULL DEFAULT 'stored',
                    page_count integer,
                    pages_processed integer,
                    chunk_count integer,
                    vector_ids_count integer,
                    reports_rows integer,
                    error_message text,
                    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
                    created_at timestamptz NOT NULL DEFAULT now(),
                    updated_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id uuid PRIMARY KEY,
                    company_id uuid NOT NULL REFERENCES companies(id),
                    document_id uuid REFERENCES documents(id),
                    document_name text,
                    source_path text NOT NULL,
                    upload_status text,
                    content text NOT NULL,
                    search_vector tsvector NOT NULL,
                    embedding vector,
                    page_number integer,
                    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
                    created_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS document_id uuid REFERENCES documents(id)")
            cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS document_name text")
            cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS upload_status text")
            cur.execute("CREATE INDEX IF NOT EXISTS documents_company_id_idx ON documents(company_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS documents_status_idx ON documents(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS reports_company_id_idx ON reports(company_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS reports_document_id_idx ON reports(document_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS reports_search_vector_idx ON reports USING GIN(search_vector)")
        conn.commit()


def sync_chunks_to_project_tables(
    settings: Settings,
    chunks: Sequence[Document],
    replace_source: bool = True,
    document_id: str | None = None,
) -> int:
    ensure_project_schema(settings)
    inserted = 0
    with psycopg.connect(settings.psycopg_dsn) as conn:
        with conn.cursor() as cur:
            if replace_source:
                source_paths = sorted({chunk.metadata["source_path"] for chunk in chunks})
                for source_path in source_paths:
                    cur.execute("DELETE FROM reports WHERE source_path = %s", (source_path,))

            company_ids: dict[str, str] = {}
            for chunk in chunks:
                ticker = str(chunk.metadata["ticker"])
                if ticker not in company_ids:
                    company_ids[ticker] = _upsert_company(
                        cur,
                        ticker=ticker,
                        name=str(chunk.metadata["company_name"]),
                    )
                cur.execute(
                    """
                    INSERT INTO reports (
                        id,
                        company_id,
                        document_id,
                        document_name,
                        source_path,
                        upload_status,
                        content,
                        search_vector,
                        embedding,
                        page_number,
                        metadata
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        to_tsvector('english', %s),
                        NULL,
                        %s,
                        %s
                    )
                    """,
                    (
                        str(uuid4()),
                        company_ids[ticker],
                        document_id,
                        chunk.metadata.get("source_file"),
                        chunk.metadata["source_path"],
                        "completed",
                        chunk.page_content,
                        _search_text(chunk),
                        chunk.metadata.get("page_number"),
                        Jsonb(chunk.metadata),
                    ),
                )
                inserted += 1
        conn.commit()
    return inserted


def full_text_search(
    settings: Settings,
    query: str,
    ticker: str | None = None,
    limit: int = 5,
) -> list[dict[str, object]]:
    settings.require_database()
    where = ["reports.search_vector @@ plainto_tsquery('english', %s)"]
    params: list[object] = [query, query]
    if ticker:
        where.append("companies.ticker = %s")
        params.append(ticker)
    params.append(limit)

    sql = f"""
        SELECT
            reports.id,
            companies.ticker,
            companies.name AS company_name,
            reports.content,
            reports.metadata,
            ts_rank_cd(reports.search_vector, plainto_tsquery('english', %s)) AS full_text_rank
        FROM reports
        JOIN companies ON companies.id = reports.company_id
        WHERE {' AND '.join(where)}
        ORDER BY full_text_rank DESC
        LIMIT %s
    """
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return [
        {
            "id": (row["metadata"] or {}).get("chunk_id") or str(row["id"]),
            "report_id": str(row["id"]),
            "ticker": row["ticker"],
            "company_name": row["company_name"],
            "content": row["content"],
            "metadata": row["metadata"],
            "full_text_rank": float(row["full_text_rank"]),
        }
        for row in rows
    ]


def vector_search(
    settings: Settings,
    query: str,
    ticker: str | None = None,
    limit: int = 5,
) -> list[dict[str, object]]:
    embeddings = build_embeddings(settings)
    vector_store = build_vector_store(settings, embeddings, reset_collection=False)
    filter_arg = {"ticker": ticker} if ticker else None
    results = vector_store.similarity_search_with_score(query=query, k=limit, filter=filter_arg)
    return [
        {
            "id": doc.metadata.get("chunk_id") or doc.id,
            "ticker": doc.metadata.get("ticker"),
            "company_name": doc.metadata.get("company_name"),
            "content": doc.page_content,
            "metadata": doc.metadata,
            "vector_distance": float(score),
        }
        for doc, score in results
    ]


def hybrid_search(
    settings: Settings,
    query: str,
    ticker: str | None = None,
    limit: int = 5,
    candidate_limit: int = 20,
    rrf_k: int = 60,
) -> list[dict[str, object]]:
    full_text_results = full_text_search(settings, query=query, ticker=ticker, limit=candidate_limit)
    vector_results = vector_search(settings, query=query, ticker=ticker, limit=candidate_limit)

    fused: dict[str, dict[str, object]] = {}
    for rank, row in enumerate(full_text_results, start=1):
        key = str(row["id"])
        fused.setdefault(key, dict(row, vector_distance=None, rrf_score=0.0))
        fused[key]["full_text_rank"] = row["full_text_rank"]
        fused[key]["full_text_position"] = rank
        fused[key]["rrf_score"] = float(fused[key]["rrf_score"]) + 1.0 / (rrf_k + rank)

    for rank, row in enumerate(vector_results, start=1):
        key = str(row["id"])
        fused.setdefault(key, dict(row, full_text_rank=None, rrf_score=0.0))
        fused[key]["vector_distance"] = row["vector_distance"]
        fused[key]["vector_position"] = rank
        fused[key]["rrf_score"] = float(fused[key]["rrf_score"]) + 1.0 / (rrf_k + rank)

    return sorted(fused.values(), key=lambda item: float(item["rrf_score"]), reverse=True)[:limit]


def _upsert_company(cur: psycopg.Cursor, ticker: str, name: str) -> str:
    company_id = str(uuid4())
    cur.execute(
        """
        INSERT INTO companies (id, ticker, name, status)
        VALUES (%s, %s, %s, 'processing')
        ON CONFLICT (ticker)
        DO UPDATE SET name = EXCLUDED.name, updated_at = now()
        RETURNING id
        """,
        (company_id, ticker, name),
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"Failed to upsert company {ticker}")
    return str(row[0])


def _document_id(document: Document) -> str:
    return str(document.id or document.metadata["chunk_id"])


def _search_text(chunk: Document) -> str:
    parts: Iterable[object] = (
        chunk.metadata.get("ticker"),
        chunk.metadata.get("company_name"),
        chunk.metadata.get("filing_type"),
        chunk.metadata.get("heading_path"),
        chunk.page_content,
    )
    return " ".join(str(part) for part in parts if part)
