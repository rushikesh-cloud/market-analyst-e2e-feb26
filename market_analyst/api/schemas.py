from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


DocumentLifecycleStatus = Literal["uploaded", "processing", "completed", "failed"]
DocumentStageName = Literal["stored", "extracting_markdown", "chunking", "embedding", "syncing_reports", "completed", "failed"]


class DocumentStageHistoryEntry(ApiModel):
    stage: DocumentStageName
    status: Literal["completed", "running", "upcoming", "failed"]
    started_at: datetime | None = Field(default=None, alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


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
    status: DocumentLifecycleStatus
    stage: DocumentStageName
    page_count: int | None = Field(default=None, alias="pageCount")
    pages_processed: int | None = Field(default=None, alias="pagesProcessed")
    chunk_count: int | None = Field(default=None, alias="chunkCount")
    vector_ids_count: int | None = Field(default=None, alias="vectorIdsCount")
    reports_rows: int | None = Field(default=None, alias="reportsRows")
    error_message: str | None = Field(default=None, alias="errorMessage")
    metadata: dict[str, Any] = Field(default_factory=dict)
    stage_history: list[DocumentStageHistoryEntry] = Field(default_factory=list, alias="stageHistory")
    uploaded_at: datetime = Field(alias="uploadedAt")
    updated_at: datetime = Field(alias="updatedAt")


class SupervisorRunCreateRequest(ApiModel):
    company_id: UUID = Field(alias="companyId")
    document_id: UUID = Field(alias="documentId")


class SupervisorChatMessage(ApiModel):
    role: Literal["user", "assistant"]
    content: str


class SupervisorRunChatRequest(ApiModel):
    message: str
    history: list[SupervisorChatMessage] = Field(default_factory=list)
    max_history_messages: int = Field(default=12, alias="maxHistoryMessages")


class SupervisorRunChatResponse(ApiModel):
    answer: str
    history: list[SupervisorChatMessage]
    tool_names: list[str] = Field(default_factory=list, alias="toolNames")


class SupervisorRunResponse(ApiModel):
    id: UUID
    company_id: UUID = Field(alias="companyId")
    company_name: str = Field(alias="companyName")
    ticker: str
    yahoo_finance_ticker: str | None = Field(default=None, alias="yahooFinanceTicker")
    sector: str | None = None
    document_id: UUID = Field(alias="documentId")
    document_name: str = Field(alias="documentName")
    document_status: str = Field(alias="documentStatus")
    status: Literal["queued", "running", "completed", "failed"]
    error_message: str | None = Field(default=None, alias="errorMessage")
    final_rating: int | None = Field(default=None, alias="finalRating")
    fundamental_status: str = Field(alias="fundamentalStatus")
    technical_status: str = Field(alias="technicalStatus")
    news_status: str = Field(alias="newsStatus")
    fundamental: dict[str, Any] | None = None
    technical: dict[str, Any] | None = None
    news: dict[str, Any] | None = None
    supervisor: dict[str, Any] | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
