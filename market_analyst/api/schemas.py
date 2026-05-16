from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class CompanyCreateRequest(ApiModel):
    name: str
    ticker: str
    yahoo_finance_ticker: str = Field(alias="yahooFinanceTicker")
    sector: str
    status: str = "pending"
    overall_score: float | None = Field(default=None, alias="overallScore")


class CompanyUpdateRequest(ApiModel):
    name: str
    ticker: str
    yahoo_finance_ticker: str = Field(alias="yahooFinanceTicker")
    sector: str
    status: str
    overall_score: float | None = Field(default=None, alias="overallScore")


class CompanyResponse(ApiModel):
    id: UUID
    name: str
    ticker: str
    yahoo_finance_ticker: str | None = Field(default=None, alias="yahooFinanceTicker")
    sector: str | None = None
    overall_score: float | None = Field(default=None, alias="overallScore")
    status: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class DocumentResponse(ApiModel):
    id: UUID
    company_id: UUID = Field(alias="companyId")
    company_name: str = Field(alias="companyName")
    document_name: str = Field(alias="documentName")
    file_name: str = Field(alias="fileName")
    content_type: str | None = Field(default=None, alias="contentType")
    file_size: int = Field(alias="fileSize")
    source_path: str = Field(alias="sourcePath")
    status: Literal["uploaded", "processing", "completed", "failed"]
    stage: Literal["stored", "extracting_markdown", "chunking", "embedding", "syncing_reports", "completed", "failed"]
    page_count: int | None = Field(default=None, alias="pageCount")
    pages_processed: int | None = Field(default=None, alias="pagesProcessed")
    chunk_count: int | None = Field(default=None, alias="chunkCount")
    vector_ids_count: int | None = Field(default=None, alias="vectorIdsCount")
    reports_rows: int | None = Field(default=None, alias="reportsRows")
    error_message: str | None = Field(default=None, alias="errorMessage")
    metadata: dict[str, Any] = Field(default_factory=dict)
    uploaded_at: datetime = Field(alias="uploadedAt")
    updated_at: datetime = Field(alias="updatedAt")
