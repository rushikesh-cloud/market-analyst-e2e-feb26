from __future__ import annotations

from urllib.parse import urlencode

import httpx

from market_analyst.config.settings import Settings
from market_analyst.types.auth import GoogleTokenExchangeResult, GoogleUserProfile


GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def build_google_authorization_url(settings: Settings, state: str) -> str:
    settings.require_google_oauth()
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
    )
    return f"{GOOGLE_AUTHORIZATION_URL}?{query}"


def exchange_google_code(settings: Settings, code: str) -> GoogleTokenExchangeResult:
    settings.require_google_oauth()
    response = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()
    return GoogleTokenExchangeResult(
        access_token=str(payload["access_token"]),
        id_token=str(payload["id_token"]) if payload.get("id_token") else None,
    )


def fetch_google_user_profile(access_token: str) -> GoogleUserProfile:
    response = httpx.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()
    return GoogleUserProfile(
        subject=str(payload["sub"]),
        email=str(payload["email"]).strip().lower(),
        email_verified=bool(payload.get("email_verified")),
        given_name=str(payload.get("given_name") or "").strip(),
        family_name=str(payload.get("family_name") or "").strip(),
        full_name=str(payload.get("name") or "").strip(),
    )
