from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from market_analyst.api.dependencies import get_settings
from market_analyst.api.schemas import (
    SupervisorRunChatRequest,
    SupervisorRunChatResponse,
    SupervisorRunCreateRequest,
    SupervisorRunResponse,
)
from market_analyst.config.settings import PROJECT_ROOT, Settings
from market_analyst.repositories.companies import get_company
from market_analyst.repositories.documents import get_document
from market_analyst.repositories.supervisor_runs import create_supervisor_run, get_supervisor_run, list_supervisor_runs
from market_analyst.services.supervisor_chat import run_supervisor_chat_turn, stream_supervisor_chat_turn
from market_analyst.services.supervisor_runs import execute_supervisor_run
from market_analyst.types.supervisor import SupervisorAnalysisResult, SupervisorRatingComponent
from market_analyst.types.supervisor_chat import (
    SupervisorChatContext,
    SupervisorChatMessage as DomainSupervisorChatMessage,
    SupervisorChatRequest as DomainSupervisorChatRequest,
)


router = APIRouter(prefix="/supervisor-runs", tags=["supervisor-runs"])


@router.get("", response_model=list[SupervisorRunResponse])
def get_supervisor_runs(settings: Settings = Depends(get_settings)) -> list[dict[str, object]]:
    return list_supervisor_runs(settings)


@router.post("", response_model=SupervisorRunResponse, status_code=202)
def post_supervisor_run(
    request: SupervisorRunCreateRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    company = get_company(settings, str(request.company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    document = get_document(settings, str(request.document_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if str(document["company_id"]) != str(request.company_id):
        raise HTTPException(status_code=409, detail="Document does not belong to the selected company")
    if str(document["status"]) != "completed":
        raise HTTPException(status_code=409, detail="Document ingestion must be completed before starting a supervisor run")

    run = create_supervisor_run(
        settings,
        company_id=str(request.company_id),
        document_id=str(request.document_id),
    )
    background_tasks.add_task(execute_supervisor_run, settings, str(run["id"]))
    return run


@router.get("/{run_id}", response_model=SupervisorRunResponse)
def get_supervisor_run_status(
    run_id: str,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    run = get_supervisor_run(settings, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Supervisor run not found")
    return run


@router.post("/{run_id}/chat", response_model=SupervisorRunChatResponse)
def post_supervisor_run_chat(
    run_id: str,
    request: SupervisorRunChatRequest,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    run = get_supervisor_run(settings, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Supervisor run not found")
    if str(run.get("status")) != "completed":
        raise HTTPException(status_code=409, detail="Supervisor chat is available only after the run completes")

    response = run_supervisor_chat_turn(
        settings,
        DomainSupervisorChatRequest(
            context=_build_chat_context(run),
            message=request.message,
            history=[DomainSupervisorChatMessage(role=item.role, content=item.content) for item in request.history],
            max_history_messages=request.max_history_messages,
        ),
    )
    return {
        "answer": response.answer,
        "history": [{"role": item.role, "content": item.content} for item in response.history],
        "toolNames": response.tool_names,
    }


@router.post("/{run_id}/chat/stream")
def post_supervisor_run_chat_stream(
    run_id: str,
    request: SupervisorRunChatRequest,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    run = get_supervisor_run(settings, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Supervisor run not found")
    if str(run.get("status")) != "completed":
        raise HTTPException(status_code=409, detail="Supervisor chat is available only after the run completes")

    domain_request = DomainSupervisorChatRequest(
        context=_build_chat_context(run),
        message=request.message,
        history=[DomainSupervisorChatMessage(role=item.role, content=item.content) for item in request.history],
        max_history_messages=request.max_history_messages,
    )

    def event_stream():
        try:
            for event in stream_supervisor_chat_turn(settings, domain_request):
                yield json.dumps(event) + "\n"
        except Exception as exc:
            yield json.dumps({"type": "error", "message": str(exc)}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.get("/{run_id}/technical-chart")
def get_supervisor_run_technical_chart(
    run_id: str,
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    run = get_supervisor_run(settings, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Supervisor run not found")

    technical = run.get("technical")
    chart_path = technical.get("chart_path") if isinstance(technical, dict) else None
    if not isinstance(chart_path, str) or not chart_path.strip():
        raise HTTPException(status_code=404, detail="Technical chart not available for this run")

    file_path = Path(chart_path).expanduser().resolve()
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Technical chart file not found")
    try:
        file_path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Technical chart file is outside the allowed project scope") from exc

    media_type = "image/png"
    if file_path.suffix.lower() in {".jpg", ".jpeg"}:
        media_type = "image/jpeg"
    elif file_path.suffix.lower() == ".webp":
        media_type = "image/webp"
    return FileResponse(path=file_path, media_type=media_type, filename=file_path.name)


def _build_chat_context(run: dict[str, object]) -> SupervisorChatContext:
    return SupervisorChatContext(
        company_name=str(run.get("company_name") or run.get("companyName") or ""),
        ticker=str(run.get("yahoo_finance_ticker") or run.get("yahooFinanceTicker") or run.get("ticker") or ""),
        sector=str(run["sector"]) if isinstance(run.get("sector"), str) else None,
        supervisor_result=_parse_supervisor_result(run, run.get("supervisor")),
    )


def _parse_supervisor_result(run: dict[str, object], value: object) -> SupervisorAnalysisResult | None:
    if not isinstance(value, dict):
        return None

    final_rating = value.get("final_rating")
    summary = value.get("summary")
    components_raw = value.get("components")
    if not isinstance(final_rating, int) or not isinstance(summary, str) or not isinstance(components_raw, list):
        return None

    components: list[SupervisorRatingComponent] = []
    for item in components_raw:
        if not isinstance(item, dict):
            continue
        weight = item.get("weight")
        components.append(
            SupervisorRatingComponent(
                name=str(item.get("name") or "unknown"),
                rating=item.get("rating") if isinstance(item.get("rating"), int) else None,
                weight=float(weight) if isinstance(weight, (float, int)) else 0.0,
                rationale=str(item.get("rationale") or ""),
            )
        )

    return SupervisorAnalysisResult(
        company_name=str(
            value.get("company_name")
            or value.get("companyName")
            or run.get("company_name")
            or run.get("companyName")
            or ""
        ),
        ticker=str(value.get("ticker") or run.get("yahoo_finance_ticker") or run.get("yahooFinanceTicker") or run.get("ticker") or ""),
        final_rating=final_rating,
        summary=summary,
        components=components,
        metadata=value.get("metadata") if isinstance(value.get("metadata"), dict) else {},
    )
