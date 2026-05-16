from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any
from uuid import UUID
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from market_analyst.config.settings import Settings
from market_analyst.repositories.vector_db import ensure_project_schema


RUN_COLUMNS = """
    analysis_results.id,
    analysis_results.company_id,
    companies.name AS company_name,
    companies.ticker,
    companies.yahoo_finance_ticker,
    companies.sector,
    analysis_results.document_id,
    documents.document_name,
    documents.status AS document_status,
    analysis_results.status,
    analysis_results.error_message,
    analysis_results.fundamental_status,
    analysis_results.technical_status,
    analysis_results.news_status,
    analysis_results.fundamental_json,
    analysis_results.technical_json,
    analysis_results.news_json,
    analysis_results.supervisor_summary,
    analysis_results.created_at,
    analysis_results.updated_at
"""


def list_supervisor_runs(settings: Settings) -> list[dict[str, object]]:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {RUN_COLUMNS}
                FROM analysis_results
                JOIN companies ON companies.id = analysis_results.company_id
                JOIN documents ON documents.id = analysis_results.document_id
                ORDER BY analysis_results.created_at DESC
                """
            )
            return [_serialize_supervisor_run_row(row) for row in cur.fetchall()]


def get_supervisor_run(settings: Settings, run_id: str) -> dict[str, object] | None:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {RUN_COLUMNS}
                FROM analysis_results
                JOIN companies ON companies.id = analysis_results.company_id
                JOIN documents ON documents.id = analysis_results.document_id
                WHERE analysis_results.id = %s
                """,
                (run_id,),
            )
            row = cur.fetchone()
    return _serialize_supervisor_run_row(row) if row else None


def create_supervisor_run(
    settings: Settings,
    *,
    company_id: str,
    document_id: str,
) -> dict[str, object]:
    ensure_project_schema(settings)
    run_id = str(uuid4())
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analysis_results (
                    id,
                    company_id,
                    document_id,
                    status,
                    fundamental_status,
                    technical_status,
                    news_status
                )
                VALUES (%s, %s, %s, 'queued', 'idle', 'idle', 'idle')
                RETURNING id
                """,
                (run_id, company_id, document_id),
            )
        conn.commit()
    created = get_supervisor_run(settings, run_id)
    if created is None:
        raise RuntimeError(f"Failed to create supervisor run {run_id}")
    return created


def update_supervisor_run(
    settings: Settings,
    run_id: str,
    *,
    status: str | None = None,
    error_message: str | None = None,
    fundamental_status: str | None = None,
    technical_status: str | None = None,
    news_status: str | None = None,
    fundamental: Mapping[str, object] | None = None,
    technical: Mapping[str, object] | None = None,
    news: Mapping[str, object] | None = None,
    supervisor: Mapping[str, object] | None = None,
) -> dict[str, object]:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE analysis_results
                SET
                    status = COALESCE(%s, status),
                    error_message = %s,
                    fundamental_status = COALESCE(%s, fundamental_status),
                    technical_status = COALESCE(%s, technical_status),
                    news_status = COALESCE(%s, news_status),
                    fundamental_json = COALESCE(%s, fundamental_json),
                    technical_json = COALESCE(%s, technical_json),
                    news_json = COALESCE(%s, news_json),
                    supervisor_summary = COALESCE(%s, supervisor_summary),
                    updated_at = now()
                WHERE id = %s
                """,
                (
                    status,
                    error_message,
                    fundamental_status,
                    technical_status,
                    news_status,
                    Jsonb(dict(fundamental)) if fundamental is not None else None,
                    Jsonb(dict(technical)) if technical is not None else None,
                    Jsonb(dict(news)) if news is not None else None,
                    Jsonb(dict(supervisor)) if supervisor is not None else None,
                    run_id,
                ),
            )
        conn.commit()
    updated = get_supervisor_run(settings, run_id)
    if updated is None:
        raise RuntimeError(f"Supervisor run not found after update: {run_id}")
    return updated


def _serialize_supervisor_run_row(row: dict[str, Any]) -> dict[str, object]:
    serialized = dict(row)
    for key in ("id", "company_id", "document_id"):
        if isinstance(serialized.get(key), UUID):
            serialized[key] = str(serialized[key])
    serialized["final_rating"] = _extract_final_rating(serialized.get("supervisor_summary"))
    for key in ("fundamental_json", "technical_json", "news_json", "supervisor_summary"):
        value = serialized.get(key)
        if isinstance(value, dict):
            serialized[key] = _convert_nested_decimals(value)
    serialized["fundamental"] = serialized.pop("fundamental_json", None)
    serialized["technical"] = serialized.pop("technical_json", None)
    serialized["news"] = serialized.pop("news_json", None)
    serialized["supervisor"] = serialized.pop("supervisor_summary", None)
    return serialized


def _extract_final_rating(supervisor_summary: object) -> int | None:
    if not isinstance(supervisor_summary, dict):
        return None
    value = supervisor_summary.get("final_rating")
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _convert_nested_decimals(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _convert_nested_decimals(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_convert_nested_decimals(item) for item in value]
    return value
