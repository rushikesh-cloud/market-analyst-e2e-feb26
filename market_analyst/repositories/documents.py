from __future__ import annotations

from datetime import UTC, datetime
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
    documents.stage_history,
    documents.created_at AS uploaded_at,
    documents.updated_at
"""

ACTIVE_DOCUMENT_STAGES = ("stored", "extracting_markdown", "chunking", "embedding", "syncing_reports")
DOCUMENT_STAGE_SEQUENCE = (*ACTIVE_DOCUMENT_STAGES, "completed")


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
    now = _utc_now()
    stage_history = [
        {
            "stage": "stored",
            "status": "completed",
            "started_at": _isoformat(now),
            "completed_at": _isoformat(now),
        }
    ]
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
                    metadata,
                    stage_history
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'uploaded', 'stored', %s, %s)
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
                    Jsonb(stage_history),
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
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT stage_history FROM documents WHERE id = %s", (document_id,))
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(f"Document not found before update: {document_id}")
            stage_history = _advance_stage_history(row.get("stage_history"), stage=stage, lifecycle_status=status)
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
                    stage_history = %s,
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
                    Jsonb(stage_history),
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
    serialized["stage_history"] = _normalize_stage_history(serialized.get("stage_history"))
    return serialized


def _advance_stage_history(
    current_history: Any,
    *,
    stage: str,
    lifecycle_status: str,
    now: datetime | None = None,
) -> list[dict[str, str | None]]:
    timestamp = now or _utc_now()
    next_history = _normalize_stage_history(current_history)
    timestamp_value = _isoformat(timestamp)

    for entry in next_history:
        if entry["status"] == "running" and entry["completed_at"] is None:
            entry["status"] = "completed" if lifecycle_status != "failed" else entry["status"]
            if lifecycle_status != "failed":
                entry["completed_at"] = timestamp_value

    stage_entry = next((entry for entry in next_history if entry["stage"] == stage), None)
    if stage_entry is None:
        stage_entry = {
            "stage": stage,
            "status": "running",
            "started_at": timestamp_value,
            "completed_at": None,
        }
        next_history.append(stage_entry)
    elif stage_entry["started_at"] is None:
        stage_entry["started_at"] = timestamp_value

    if lifecycle_status == "processing":
        stage_entry["status"] = "running"
        stage_entry["completed_at"] = None
    elif lifecycle_status == "completed":
        stage_entry["status"] = "completed"
        stage_entry["completed_at"] = stage_entry["completed_at"] or timestamp_value
    elif lifecycle_status == "failed":
        stage_entry["status"] = "failed"
        stage_entry["completed_at"] = timestamp_value
    else:
        stage_entry["status"] = "completed"
        stage_entry["completed_at"] = stage_entry["completed_at"] or timestamp_value

    return _normalize_stage_history(next_history)


def _normalize_stage_history(value: Any) -> list[dict[str, str | None]]:
    current_entries = value if isinstance(value, list) else []
    history_by_stage: dict[str, dict[str, str | None]] = {}
    for raw_entry in current_entries:
        if not isinstance(raw_entry, dict):
            continue
        stage = str(raw_entry.get("stage") or "").strip()
        if not stage:
            continue
        history_by_stage[stage] = {
            "stage": stage,
            "status": _normalize_stage_status(raw_entry.get("status")),
            "started_at": _coerce_iso_timestamp(raw_entry.get("started_at")),
            "completed_at": _coerce_iso_timestamp(raw_entry.get("completed_at")),
        }

    ordered: list[dict[str, str | None]] = []
    for stage_name in DOCUMENT_STAGE_SEQUENCE:
        entry = history_by_stage.pop(stage_name, None)
        if entry:
            ordered.append(entry)
        elif stage_name != "completed":
            ordered.append(
                {
                    "stage": stage_name,
                    "status": "upcoming",
                    "started_at": None,
                    "completed_at": None,
                }
            )

    if "failed" in history_by_stage:
        ordered.append(history_by_stage.pop("failed"))
    ordered.extend(history_by_stage.values())
    return ordered


def _normalize_stage_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    if status in {"completed", "running", "upcoming", "failed"}:
        return status
    return "upcoming"


def _coerce_iso_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _isoformat(value)
    text = str(value).strip()
    return text or None


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()
