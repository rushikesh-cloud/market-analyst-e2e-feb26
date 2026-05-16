from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from market_analyst.config.settings import Settings, load_settings
from market_analyst.repositories.auth import get_user_by_session_token


def get_settings() -> Settings:
    return load_settings()


def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, object] | None:
    token = request.cookies.get(settings.auth_session_cookie_name)
    if token is None:
        return None
    return get_user_by_session_token(settings, token)


def require_authenticated_user(
    current_user: dict[str, object] | None = Depends(get_current_user),
) -> dict[str, object]:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user
