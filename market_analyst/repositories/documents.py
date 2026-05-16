from __future__ import annotations

from typing import Any
from uuid import UUID
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from market_analyst.config.settings import Settings
from market_analyst.repositories.vector_db import ensure_project_schema


DOCUMENT_COLUMNS = """
    documents.id,
    documents.company_id,
    companies.name AS company_name,
    documents.document_name,
    documents.file_name,
    documents.content_type,
    documents.file_size,
    documents.source_path,
    documents.status,
    documents.stage,
    documents.page_count,
    documents.pages_processed,
    documents.chunk_count,
    documents.vector_ids_count,
    documents.reports_rows,
    documents.error_message,
    documents.metadata,
    documents.created_at AS uploaded_at,
    documents.updated_at
"""


def list_documents(settings: Settings, company_id: str | None = None) -> list[dict[str, object]]:
    ensure_project_schema(settings)
    where = ""
    params: tuple[object, ...] = ()
    if company_id:
        where = "WHERE documents.company_id = %s"
        params = (company_id,)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {DOCUMENT_COLUMNS}
                FROM documents
                JOIN companies ON companies.id = documents.company_id
                {where}
                ORDER BY documents.created_at DESC
                """,
                params,
            )
            return [_serialize_document_row(row) for row in cur.fetchall()]


def get_document(settings: Settings, document_id: str) -> dict[str, object] | None:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {DOCUMENT_COLUMNS}
                FROM documents
                JOIN companies ON companies.id = documents.company_id
                WHERE documents.id = %s
                """,
                (document_id,),
            )
            row = cur.fetchone()
    return _serialize_document_row(row) if row else None


def create_document(
    settings: Settings,
    *,
    company_id: str,
    document_name: str,
    file_name: str,
    content_type: str | None,
    file_size: int,
    source_path: str,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    ensure_project_schema(settings)
    document_id = str(uuid4())
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (
                    id,
                    company_id,
                    document_name,
                    file_name,
                    content_type,
                    file_size,
                    source_path,
                    status,
                    stage,
                    metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'uploaded', 'stored', %s)
                RETURNING id
                """,
                (
                    document_id,
                    company_id,
                    document_name,
                    file_name,
                    content_type,
                    file_size,
                    source_path,
                    Jsonb(metadata or {}),
                ),
            )
        conn.commit()
    created = get_document(settings, document_id)
    if created is None:
        raise RuntimeError(f"Failed to create document {document_name}")
    return created


def update_document_status(
    settings: Settings,
    document_id: str,
    *,
    status: str,
    stage: str,
    page_count: int | None = None,
    pages_processed: int | None = None,
    chunk_count: int | None = None,
    vector_ids_count: int | None = None,
    reports_rows: int | None = None,
    error_message: str | None = None,
) -> dict[str, object]:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE documents
                SET
                    status = %s,
                    stage = %s,
                    page_count = COALESCE(%s, page_count),
                    pages_processed = COALESCE(%s, pages_processed),
                    chunk_count = COALESCE(%s, chunk_count),
                    vector_ids_count = COALESCE(%s, vector_ids_count),
                    reports_rows = COALESCE(%s, reports_rows),
                    error_message = %s,
                    updated_at = now()
                WHERE id = %s
                """,
                (
                    status,
                    stage,
                    page_count,
                    pages_processed,
                    chunk_count,
                    vector_ids_count,
                    reports_rows,
                    error_message,
                    document_id,
                ),
            )
        conn.commit()
    updated = get_document(settings, document_id)
    if updated is None:
        raise RuntimeError(f"Document not found after update: {document_id}")
    return updated


def _serialize_document_row(row: dict[str, Any]) -> dict[str, object]:
    serialized = dict(row)
    for key in ("id", "company_id"):
        if isinstance(serialized.get(key), UUID):
            serialized[key] = str(serialized[key])
    return serialized
