from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from market_analyst.api.dependencies import get_settings
from market_analyst.api.schemas import CompanyCreateRequest, CompanyResponse, CompanyUpdateRequest
from market_analyst.config.settings import Settings
from market_analyst.repositories.companies import create_company, list_companies, update_company


router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyResponse])
def get_companies(settings: Settings = Depends(get_settings)) -> list[dict[str, object]]:
    return list_companies(settings)


@router.post("", response_model=CompanyResponse, status_code=201)
def post_company(
    request: CompanyCreateRequest,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return create_company(
        settings,
        name=request.name,
        ticker=request.ticker,
        yahoo_finance_ticker=request.yahoo_finance_ticker,
        sector=request.sector,
        status=request.status,
        overall_score=request.overall_score,
    )


@router.put("/{company_id}", response_model=CompanyResponse)
def put_company(
    company_id: str,
    request: CompanyUpdateRequest,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    company = update_company(
        settings,
        company_id=company_id,
        name=request.name,
        ticker=request.ticker,
        yahoo_finance_ticker=request.yahoo_finance_ticker,
        sector=request.sector,
        status=request.status,
        overall_score=request.overall_score,
    )
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company
