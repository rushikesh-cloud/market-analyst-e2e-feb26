from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

from market_analyst.api.dependencies import get_current_user, get_settings
from market_analyst.api.schemas import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthUserResponse,
)
from market_analyst.config.settings import Settings
from market_analyst.services.auth import (
    authenticate_with_google,
    create_google_authorization_redirect,
    login_user,
    logout_user,
    register_user,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthUserResponse, status_code=201)
def post_register(request: AuthRegisterRequest, response: Response, settings: Settings = Depends(get_settings)) -> dict[str, object]:
    user, session_token, expires_at = register_user(
        settings,
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        mobile_number=request.mobile_number,
        gender=request.gender,
        dob=request.dob,
        password=request.password,
        confirm_password=request.confirm_password,
    )
    _set_session_cookie(response, settings, session_token, expires_at)
    return user


@router.post("/login", response_model=AuthUserResponse)
def post_login(request: AuthLoginRequest, response: Response, settings: Settings = Depends(get_settings)) -> dict[str, object]:
    user, session_token, expires_at = login_user(
        settings,
        email=request.email,
        password=request.password,
    )
    _set_session_cookie(response, settings, session_token, expires_at)
    return user


@router.post("/logout", status_code=204)
def post_logout(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> Response:
    logout_user(settings, request.cookies.get(settings.auth_session_cookie_name))
    _clear_session_cookie(response, settings)
    response.status_code = 204
    return response


@router.get("/me", response_model=AuthUserResponse)
def get_me(current_user: dict[str, object] | None = Depends(get_current_user)) -> dict[str, object]:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user


@router.get("/google/start")
def start_google_auth(
    settings: Settings = Depends(get_settings),
    next: str = Query(default="/"),
) -> RedirectResponse:
    return RedirectResponse(create_google_authorization_redirect(settings, next), status_code=302)


@router.get("/google/callback")
def google_callback(code: str, state: str | None = None, settings: Settings = Depends(get_settings)) -> RedirectResponse:
    _, session_token, expires_at, next_path = authenticate_with_google(settings, code=code, state=state)
    redirect_target = f"{settings.frontend_app_url}{next_path}"
    redirect = RedirectResponse(url=redirect_target, status_code=302)
    _set_session_cookie(redirect, settings, session_token, expires_at)
    return redirect


def _set_session_cookie(response: Response, settings: Settings, session_token: str, expires_at: datetime) -> None:
    response.set_cookie(
        key=settings.auth_session_cookie_name,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
        expires=expires_at,
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_session_cookie_name,
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
        path="/",
    )
