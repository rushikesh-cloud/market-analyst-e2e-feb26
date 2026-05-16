from __future__ import annotations

import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from market_analyst.api.dependencies import get_settings
from market_analyst.api.schemas import DocumentResponse
from market_analyst.config.settings import Settings
from market_analyst.repositories.companies import get_company
from market_analyst.repositories.documents import create_document, get_document, list_documents
from market_analyst.services.document_ingestion import run_document_ingestion


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
def get_documents(
    companyId: str | None = None,
    settings: Settings = Depends(get_settings),
) -> list[dict[str, object]]:
    return list_documents(settings, company_id=companyId)


@router.post("", response_model=DocumentResponse, status_code=202)
def post_document(
    background_tasks: BackgroundTasks,
    companyId: str = Form(...),
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    company = get_company(settings, companyId)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    source_path = save_upload(settings.upload_dir, companyId, file)
    document = create_document(
        settings,
        company_id=companyId,
        document_name=Path(file.filename or source_path.name).name,
        file_name=Path(file.filename or source_path.name).name,
        content_type=file.content_type,
        file_size=source_path.stat().st_size,
        source_path=str(source_path),
        metadata={"original_filename": file.filename or source_path.name},
    )
    background_tasks.add_task(run_document_ingestion, settings, str(document["id"]))
    return document


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_status(
    document_id: str,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    document = get_document(settings, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("/{document_id}/ingest", response_model=DocumentResponse, status_code=202)
def retry_document_ingestion(
    document_id: str,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    document = get_document(settings, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    background_tasks.add_task(run_document_ingestion, settings, document_id)
    return document


def save_upload(upload_dir: Path, company_id: str, upload: UploadFile) -> Path:
    filename = safe_filename(upload.filename or "document.pdf")
    target_dir = upload_dir / company_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{uuid4()}-{filename}"
    with target_path.open("wb") as output:
        shutil.copyfileobj(upload.file, output)
    return target_path


def safe_filename(filename: str) -> str:
    base = Path(filename).name.strip() or "document.pdf"
    return re.sub(r"[^A-Za-z0-9._-]+", "-", base)
