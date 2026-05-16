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

_SCHEMA_READY = False


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
    global _SCHEMA_READY

    settings.require_database()
    if _SCHEMA_READY:
        return

    with psycopg.connect(settings.psycopg_dsn) as conn:
        if _project_schema_ready(conn):
            _SCHEMA_READY = True
            return

        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(25134, 25152)")
        try:
            if _project_schema_ready(conn):
                _SCHEMA_READY = True
                return

            _create_project_schema(conn)
            _SCHEMA_READY = True
        finally:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(25134, 25152)")


def _create_project_schema(conn: psycopg.Connection) -> None:
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
                stage_history jsonb NOT NULL DEFAULT '[]'::jsonb,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS stage_history jsonb NOT NULL DEFAULT '[]'::jsonb")
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
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_results (
                id uuid PRIMARY KEY,
                company_id uuid NOT NULL REFERENCES companies(id),
                document_id uuid REFERENCES documents(id),
                status text NOT NULL DEFAULT 'queued',
                error_message text,
                fundamental_status text NOT NULL DEFAULT 'idle',
                technical_status text NOT NULL DEFAULT 'idle',
                news_status text NOT NULL DEFAULT 'idle',
                fundamental_json jsonb,
                technical_json jsonb,
                news_json jsonb,
                supervisor_summary jsonb,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id uuid PRIMARY KEY,
                first_name text NOT NULL,
                last_name text NOT NULL,
                email text UNIQUE NOT NULL,
                mobile_number text NOT NULL,
                gender text NOT NULL,
                dob date NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_identities (
                id uuid PRIMARY KEY,
                user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                provider text NOT NULL,
                provider_subject text NOT NULL,
                email text NOT NULL,
                password_salt text,
                password_hash text,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                UNIQUE(provider, provider_subject)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id uuid PRIMARY KEY,
                user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash text UNIQUE NOT NULL,
                expires_at timestamptz NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS document_id uuid REFERENCES documents(id)")
        cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS document_name text")
        cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS upload_status text")
        cur.execute("ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS document_id uuid REFERENCES documents(id)")
        cur.execute("ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'queued'")
        cur.execute("ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS error_message text")
        cur.execute("ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS fundamental_status text NOT NULL DEFAULT 'idle'")
        cur.execute("ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS technical_status text NOT NULL DEFAULT 'idle'")
        cur.execute("ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS news_status text NOT NULL DEFAULT 'idle'")
        cur.execute("ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()")
        cur.execute("CREATE INDEX IF NOT EXISTS documents_company_id_idx ON documents(company_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS documents_status_idx ON documents(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS reports_company_id_idx ON reports(company_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS reports_document_id_idx ON reports(document_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS reports_search_vector_idx ON reports USING GIN(search_vector)")
        cur.execute("CREATE INDEX IF NOT EXISTS analysis_results_company_id_idx ON analysis_results(company_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS analysis_results_document_id_idx ON analysis_results(document_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS analysis_results_status_idx ON analysis_results(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS auth_identities_user_id_idx ON auth_identities(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS auth_identities_email_idx ON auth_identities(email)")
        cur.execute("CREATE INDEX IF NOT EXISTS user_sessions_user_id_idx ON user_sessions(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS user_sessions_expires_at_idx ON user_sessions(expires_at)")
    conn.commit()


def _project_schema_ready(conn: psycopg.Connection) -> bool:
    required_columns = {
        "companies": {"id", "ticker", "yahoo_finance_ticker", "name", "sector", "overall_score", "status", "created_at", "updated_at"},
        "documents": {
            "id",
            "company_id",
            "document_name",
            "file_name",
            "content_type",
            "file_size",
            "source_path",
            "status",
            "stage",
            "page_count",
            "pages_processed",
            "chunk_count",
            "vector_ids_count",
            "reports_rows",
            "error_message",
            "metadata",
            "stage_history",
            "created_at",
            "updated_at",
        },
        "reports": {
            "id",
            "company_id",
            "document_id",
            "document_name",
            "source_path",
            "upload_status",
            "content",
            "search_vector",
            "embedding",
            "page_number",
            "metadata",
            "created_at",
        },
        "analysis_results": {
            "id",
            "company_id",
            "document_id",
            "status",
            "error_message",
            "fundamental_status",
            "technical_status",
            "news_status",
            "fundamental_json",
            "technical_json",
            "news_json",
            "supervisor_summary",
            "created_at",
            "updated_at",
        },
        "users": {
            "id",
            "first_name",
            "last_name",
            "email",
            "mobile_number",
            "gender",
            "dob",
            "created_at",
            "updated_at",
        },
        "auth_identities": {
            "id",
            "user_id",
            "provider",
            "provider_subject",
            "email",
            "password_salt",
            "password_hash",
            "created_at",
            "updated_at",
        },
        "user_sessions": {
            "id",
            "user_id",
            "token_hash",
            "expires_at",
            "created_at",
        },
    }
    required_indexes = {
        "documents_company_id_idx",
        "documents_status_idx",
        "reports_company_id_idx",
        "reports_document_id_idx",
        "reports_search_vector_idx",
        "analysis_results_company_id_idx",
        "analysis_results_document_id_idx",
        "analysis_results_status_idx",
        "auth_identities_user_id_idx",
        "auth_identities_email_idx",
        "user_sessions_user_id_idx",
        "user_sessions_expires_at_idx",
    }

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') AS installed")
        extension_row = cur.fetchone()
        if not extension_row or not extension_row["installed"]:
            return False

        cur.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = ANY(%s)
            """,
            (list(required_columns),),
        )
        actual_columns: dict[str, set[str]] = {table: set() for table in required_columns}
        for row in cur.fetchall():
            actual_columns[str(row["table_name"])].add(str(row["column_name"]))

        cur.execute(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname = ANY(%s)
            """,
            (list(required_indexes),),
        )
        actual_indexes = {str(row["indexname"]) for row in cur.fetchall()}

    return all(required_columns[table].issubset(actual_columns[table]) for table in required_columns) and required_indexes.issubset(actual_indexes)


def reset_project_schema_cache() -> None:
    global _SCHEMA_READY

    _SCHEMA_READY = False


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
            company_ids: dict[str, str] = {}
            ticker_names = {
                str(chunk.metadata["ticker"]): str(chunk.metadata["company_name"])
                for chunk in chunks
            }
            for ticker in sorted(ticker_names):
                company_ids[ticker] = _upsert_company(
                    cur,
                    ticker=ticker,
                    name=ticker_names[ticker],
                )

            if replace_source:
                source_paths = sorted({chunk.metadata["source_path"] for chunk in chunks})
                for source_path in source_paths:
                    cur.execute("DELETE FROM reports WHERE source_path = %s", (source_path,))

            for chunk in chunks:
                ticker = str(chunk.metadata["ticker"])
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
    document_id: str | None = None,
    limit: int = 5,
) -> list[dict[str, object]]:
    settings.require_database()
    where = ["reports.search_vector @@ plainto_tsquery('english', %s)"]
    params: list[object] = [query, query]
    if ticker:
        where.append("companies.ticker = %s")
        params.append(ticker)
    if document_id:
        where.append("reports.document_id = %s")
        params.append(document_id)
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
    document_id: str | None = None,
    limit: int = 5,
) -> list[dict[str, object]]:
    embeddings = build_embeddings(settings)
    vector_store = build_vector_store(settings, embeddings, reset_collection=False)
    filter_arg: dict[str, object] | None = None
    if ticker or document_id:
        filter_arg = {}
        if ticker:
            filter_arg["ticker"] = ticker
        if document_id:
            filter_arg["document_id"] = document_id
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
    document_id: str | None = None,
    limit: int = 5,
    candidate_limit: int = 20,
    rrf_k: int = 60,
) -> list[dict[str, object]]:
    full_text_results = full_text_search(
        settings,
        query=query,
        ticker=ticker,
        document_id=document_id,
        limit=candidate_limit,
    )
    vector_results = vector_search(
        settings,
        query=query,
        ticker=ticker,
        document_id=document_id,
        limit=candidate_limit,
    )

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
