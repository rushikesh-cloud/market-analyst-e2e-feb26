from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import opik

from market_analyst.config.settings import Settings
from market_analyst.repositories.companies import get_company
from market_analyst.repositories.documents import get_document
from market_analyst.repositories.supervisor_runs import get_supervisor_run, update_supervisor_run
from market_analyst.services.agents.fundamental import run_fundamental_analysis_agent
from market_analyst.services.agents.news import run_news_analysis_agent
from market_analyst.services.agents.technical import run_technical_analysis_agent
from market_analyst.services.supervisor import aggregate_supervisor_result
from market_analyst.types.fundamental import FundamentalAnalysisRequest
from market_analyst.types.news import NewsAnalysisRequest
from market_analyst.types.technical import TechnicalAnalysisRequest


@opik.track(name="execute-supervisor-run", type="general", tags=["agent", "supervisor", "orchestration"])
def execute_supervisor_run(settings: Settings, run_id: str) -> None:
    run = get_supervisor_run(settings, run_id)
    if run is None:
        raise ValueError(f"Supervisor run not found: {run_id}")

    company = get_company(settings, str(run["company_id"]))
    document = get_document(settings, str(run["document_id"]))
    if company is None:
        raise ValueError(f"Company not found for supervisor run: {run_id}")
    if document is None:
        raise ValueError(f"Document not found for supervisor run: {run_id}")

    fundamental_ticker = str(company["ticker"])
    provider_ticker = str(company.get("yahoo_finance_ticker") or company["ticker"])
    document_id = str(run["document_id"])

    try:
        update_supervisor_run(
            settings,
            run_id,
            status="running",
            error_message=None,
            fundamental_status="running",
            technical_status="idle",
            news_status="idle",
        )
        fundamental = run_fundamental_analysis_agent(
            settings,
            FundamentalAnalysisRequest(
                company_name=str(company["name"]),
                ticker=fundamental_ticker,
                document_id=document_id,
            ),
        )
        update_supervisor_run(
            settings,
            run_id,
            fundamental_status="completed",
            fundamental=_json_ready(asdict(fundamental)),
            technical_status="running",
        )

        technical = run_technical_analysis_agent(
            settings,
            TechnicalAnalysisRequest(
                ticker=provider_ticker,
            ),
        )
        update_supervisor_run(
            settings,
            run_id,
            technical_status="completed",
            technical=_json_ready(asdict(technical)),
            news_status="running",
        )

        news = run_news_analysis_agent(
            settings,
            NewsAnalysisRequest(
                company_name=str(company["name"]),
                ticker=provider_ticker,
                sector=str(company.get("sector") or "") or None,
            ),
        )
        update_supervisor_run(
            settings,
            run_id,
            news_status="completed",
            news=_json_ready(asdict(news)),
        )

        supervisor = aggregate_supervisor_result(
            company_name=str(company["name"]),
            ticker=provider_ticker,
            fundamental=fundamental,
            technical=technical,
            news=news,
        )
        update_supervisor_run(
            settings,
            run_id,
            status="completed",
            supervisor=_json_ready(asdict(supervisor)),
        )
    except Exception as exc:
        run_after_error = get_supervisor_run(settings, run_id)
        update_supervisor_run(
            settings,
            run_id,
            status="failed",
            error_message=str(exc),
            fundamental_status=_failed_status(run_after_error, "fundamental_status"),
            technical_status=_failed_status(run_after_error, "technical_status"),
            news_status=_failed_status(run_after_error, "news_status"),
        )


def _failed_status(run: dict[str, object] | None, key: str) -> str:
    current = str((run or {}).get(key, "idle"))
    if current in {"completed", "failed"}:
        return current
    return "failed" if current == "running" else current


def _json_ready(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value
