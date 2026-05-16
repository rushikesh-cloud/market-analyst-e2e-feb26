from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from market_analyst.config.settings import Settings
from market_analyst.repositories.vector_db import ensure_project_schema


def list_companies(settings: Settings) -> list[dict[str, object]]:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ticker, yahoo_finance_ticker, name, sector, overall_score, status, created_at, updated_at
                FROM companies
                ORDER BY created_at DESC
                """
            )
            return [_serialize_company_row(row) for row in cur.fetchall()]


def get_company(settings: Settings, company_id: str) -> dict[str, object] | None:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ticker, yahoo_finance_ticker, name, sector, overall_score, status, created_at, updated_at
                FROM companies
                WHERE id = %s
                """,
                (company_id,),
            )
            row = cur.fetchone()
    return _serialize_company_row(row) if row else None


def get_company_by_ticker(settings: Settings, ticker: str) -> dict[str, object] | None:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ticker, yahoo_finance_ticker, name, sector, overall_score, status, created_at, updated_at
                FROM companies
                WHERE ticker = %s
                """,
                (ticker.upper(),),
            )
            row = cur.fetchone()
    return _serialize_company_row(row) if row else None


def create_company(
    settings: Settings,
    *,
    name: str,
    ticker: str,
    yahoo_finance_ticker: str,
    sector: str,
    status: str = "pending",
    overall_score: float | None = None,
) -> dict[str, object]:
    ensure_project_schema(settings)
    company_id = str(uuid4())
    normalized_ticker = ticker.strip().upper()
    normalized_yahoo_ticker = yahoo_finance_ticker.strip().upper()
    normalized_status = status.strip().lower()
    normalized_score = overall_score if overall_score is None else float(overall_score)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO companies (id, ticker, yahoo_finance_ticker, name, sector, overall_score, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker)
                DO UPDATE SET
                    yahoo_finance_ticker = EXCLUDED.yahoo_finance_ticker,
                    name = EXCLUDED.name,
                    sector = EXCLUDED.sector,
                    overall_score = EXCLUDED.overall_score,
                    status = EXCLUDED.status,
                    updated_at = now()
                RETURNING id, ticker, yahoo_finance_ticker, name, sector, overall_score, status, created_at, updated_at
                """,
                (
                    company_id,
                    normalized_ticker,
                    normalized_yahoo_ticker,
                    name.strip(),
                    sector.strip(),
                    normalized_score,
                    normalized_status,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    if row is None:
        raise RuntimeError(f"Failed to create company {normalized_ticker}")
    return _serialize_company_row(row)


def update_company(
    settings: Settings,
    *,
    company_id: str,
    name: str,
    ticker: str,
    yahoo_finance_ticker: str,
    sector: str,
    status: str,
    overall_score: float | None,
) -> dict[str, object] | None:
    ensure_project_schema(settings)
    normalized_ticker = ticker.strip().upper()
    normalized_yahoo_ticker = yahoo_finance_ticker.strip().upper()
    normalized_status = status.strip().lower()
    normalized_score = overall_score if overall_score is None else float(overall_score)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE companies
                SET
                    ticker = %s,
                    yahoo_finance_ticker = %s,
                    name = %s,
                    sector = %s,
                    status = %s,
                    overall_score = %s,
                    updated_at = now()
                WHERE id = %s
                RETURNING id, ticker, yahoo_finance_ticker, name, sector, overall_score, status, created_at, updated_at
                """,
                (
                    normalized_ticker,
                    normalized_yahoo_ticker,
                    name.strip(),
                    sector.strip(),
                    normalized_status,
                    normalized_score,
                    company_id,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return _serialize_company_row(row) if row else None


def _serialize_company_row(row: dict[str, Any]) -> dict[str, object]:
    serialized = dict(row)
    if isinstance(serialized.get("id"), UUID):
        serialized["id"] = str(serialized["id"])
    if isinstance(serialized.get("overall_score"), Decimal):
        serialized["overall_score"] = float(serialized["overall_score"])
    return serialized
