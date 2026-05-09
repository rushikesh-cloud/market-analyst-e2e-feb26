from __future__ import annotations

from collections.abc import Iterable, Sequence
from uuid import uuid4

import psycopg
from langchain_openai import AzureOpenAIEmbeddings
from langchain_postgres import PGVector
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb

from market_analyst.config.settings import Settings
from market_analyst.types.documents import ChunkRecord


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


def embed_chunks(
    embeddings: AzureOpenAIEmbeddings,
    chunks: Sequence[ChunkRecord],
    batch_size: int = 32,
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        vectors.extend(embeddings.embed_documents([chunk.content for chunk in batch]))
    return vectors


def add_chunks_to_vector_store(
    vector_store: PGVector,
    chunks: Sequence[ChunkRecord],
    vectors: Sequence[Sequence[float]],
    batch_size: int = 32,
) -> list[str]:
    ids: list[str] = []
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        batch_vectors = vectors[start : start + batch_size]
        ids.extend(
            vector_store.add_embeddings(
                texts=[chunk.content for chunk in batch],
                embeddings=[list(vector) for vector in batch_vectors],
                metadatas=[chunk.metadata for chunk in batch],
                ids=[chunk.chunk_id for chunk in batch],
            )
        )
    return ids


def ensure_project_schema(settings: Settings) -> None:
    settings.require_database()
    with psycopg.connect(settings.psycopg_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    id uuid PRIMARY KEY,
                    ticker text UNIQUE NOT NULL,
                    name text NOT NULL,
                    overall_score numeric,
                    status text NOT NULL DEFAULT 'processing',
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
                    source_path text NOT NULL,
                    content text NOT NULL,
                    search_vector tsvector NOT NULL,
                    embedding vector,
                    page_number integer,
                    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
                    created_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS reports_company_id_idx ON reports(company_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS reports_search_vector_idx ON reports USING GIN(search_vector)")
        conn.commit()


def sync_chunks_to_project_tables(
    settings: Settings,
    chunks: Sequence[ChunkRecord],
    vectors: Sequence[Sequence[float]],
    replace_source: bool = True,
) -> int:
    if len(chunks) != len(vectors):
        raise ValueError("chunks and vectors must have the same length")

    ensure_project_schema(settings)
    inserted = 0
    with psycopg.connect(settings.psycopg_dsn) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            if replace_source:
                source_paths = sorted({chunk.metadata["source_path"] for chunk in chunks})
                for source_path in source_paths:
                    cur.execute("DELETE FROM reports WHERE source_path = %s", (source_path,))

            company_ids: dict[str, str] = {}
            for chunk, vector in zip(chunks, vectors):
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
                        source_path,
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
                        to_tsvector('english', %s),
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        str(uuid4()),
                        company_ids[ticker],
                        chunk.metadata["source_path"],
                        chunk.content,
                        _search_text(chunk),
                        list(vector),
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
    with psycopg.connect(settings.psycopg_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return [
        {
            "id": (row[4] or {}).get("chunk_id") or str(row[0]),
            "report_id": str(row[0]),
            "ticker": row[1],
            "company_name": row[2],
            "content": row[3],
            "metadata": row[4],
            "full_text_rank": float(row[5]),
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
            "id": doc.metadata.get("chunk_id"),
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


def _search_text(chunk: ChunkRecord) -> str:
    parts: Iterable[object] = (
        chunk.metadata.get("ticker"),
        chunk.metadata.get("company_name"),
        chunk.metadata.get("filing_type"),
        chunk.metadata.get("heading_path"),
        chunk.content,
    )
    return " ".join(str(part) for part in parts if part)
