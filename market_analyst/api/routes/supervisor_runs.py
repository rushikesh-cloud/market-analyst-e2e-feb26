from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from market_analyst.api.dependencies import get_settings
from market_analyst.api.schemas import SupervisorRunCreateRequest, SupervisorRunResponse
from market_analyst.config.settings import PROJECT_ROOT, Settings
from market_analyst.repositories.companies import get_company
from market_analyst.repositories.documents import get_document
from market_analyst.repositories.supervisor_runs import create_supervisor_run, get_supervisor_run, list_supervisor_runs
from market_analyst.services.supervisor_runs import execute_supervisor_run


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
