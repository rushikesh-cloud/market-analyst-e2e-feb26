from __future__ import annotations

from fastapi import APIRouter, Depends

from market_analyst.api.dependencies import get_settings
from market_analyst.api.schemas import CompanyCreateRequest, CompanyResponse
from market_analyst.config.settings import Settings
from market_analyst.repositories.companies import create_company, list_companies


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
    )
