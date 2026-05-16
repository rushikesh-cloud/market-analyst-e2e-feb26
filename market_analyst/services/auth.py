from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException

from market_analyst.config.settings import Settings
from market_analyst.providers.google_oauth import (
    build_google_authorization_url,
    exchange_google_code,
    fetch_google_user_profile,
)
from market_analyst.repositories.auth import (
    create_auth_identity,
    create_user,
    create_user_session,
    delete_user_session,
    get_auth_identity,
    get_local_identity_by_email,
    get_user_by_email,
)
from market_analyst.types.auth import GoogleUserProfile


PBKDF2_ROUNDS = 120_000


def register_user(
    settings: Settings,
    *,
    first_name: str,
    last_name: str,
    email: str,
    mobile_number: str,
    gender: str,
    dob: date,
    password: str,
    confirm_password: str,
) -> tuple[dict[str, object], str, datetime]:
    _validate_password_pair(password, confirm_password)
    normalized_email = email.strip().lower()
    existing_user = get_user_by_email(settings, normalized_email)
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    password_salt, password_hash = hash_password(password)
    user = create_user(
        settings,
        first_name=first_name,
        last_name=last_name,
        email=normalized_email,
        mobile_number=mobile_number,
        gender=gender,
        dob=dob,
    )
    create_auth_identity(
        settings,
        user_id=str(user["id"]),
        provider="local",
        provider_subject=normalized_email,
        email=normalized_email,
        password_salt=password_salt,
        password_hash=password_hash,
    )
    session_token, expires_at = create_session_for_user(settings, str(user["id"]))
    return user, session_token, expires_at


def login_user(settings: Settings, *, email: str, password: str) -> tuple[dict[str, object], str, datetime]:
    normalized_email = email.strip().lower()
    identity = get_local_identity_by_email(settings, normalized_email)
    if identity is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(
        password=password,
        salt=str(identity.get("password_salt") or ""),
        password_hash=str(identity.get("password_hash") or ""),
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = get_user_by_email(settings, normalized_email)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    session_token, expires_at = create_session_for_user(settings, str(user["id"]))
    return user, session_token, expires_at


def logout_user(settings: Settings, session_token: str | None) -> None:
    if not session_token:
        return
    delete_user_session(settings, hash_session_token(session_token))


def create_google_authorization_redirect(settings: Settings, next_path: str = "/") -> str:
    state = _encode_google_state(settings, next_path)
    return build_google_authorization_url(settings, state)


def authenticate_with_google(settings: Settings, *, code: str, state: str | None) -> tuple[dict[str, object], str, datetime, str]:
    next_path = _decode_google_state(settings, state or "")
    token_result = exchange_google_code(settings, code)
    profile = fetch_google_user_profile(token_result.access_token)
    if not profile.email_verified:
        raise HTTPException(status_code=400, detail="Google account email must be verified")

    user = _find_or_create_google_user(settings, profile)
    session_token, expires_at = create_session_for_user(settings, str(user["id"]))
    return user, session_token, expires_at, next_path


def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return base64.b64encode(salt).decode("ascii"), base64.b64encode(digest).decode("ascii")


def verify_password(*, password: str, salt: str, password_hash: str) -> bool:
    if not salt or not password_hash:
        return False
    salt_bytes = base64.b64decode(salt.encode("ascii"))
    expected = base64.b64decode(password_hash.encode("ascii"))
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, PBKDF2_ROUNDS)
    return hmac.compare_digest(candidate, expected)


def hash_session_token(session_token: str) -> str:
    return hashlib.sha256(session_token.encode("utf-8")).hexdigest()


def create_session_for_user(settings: Settings, user_id: str) -> tuple[str, datetime]:
    settings.require_auth()
    session_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(tz=UTC) + timedelta(hours=settings.auth_session_ttl_hours)
    create_user_session(
        settings,
        user_id=user_id,
        token_hash=hash_session_token(session_token),
        expires_at=expires_at,
    )
    return session_token, expires_at


def _find_or_create_google_user(settings: Settings, profile: GoogleUserProfile) -> dict[str, object]:
    google_identity = get_auth_identity(settings, "google", profile.subject)
    if google_identity is not None:
        existing = get_user_by_email(settings, profile.email)
        if existing is None:
            raise HTTPException(status_code=409, detail="Google account is linked to a missing user")
        return existing

    existing_user = get_user_by_email(settings, profile.email)
    if existing_user is None:
        existing_user = create_user(
            settings,
            first_name=profile.given_name or profile.full_name or "Google",
            last_name=profile.family_name or "User",
            email=profile.email,
            mobile_number="Google-only",
            gender="prefer_not_to_say",
            dob=date(1970, 1, 1),
        )

    create_auth_identity(
        settings,
        user_id=str(existing_user["id"]),
        provider="google",
        provider_subject=profile.subject,
        email=profile.email,
    )
    return existing_user


def _validate_password_pair(password: str, confirm_password: str) -> None:
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Password and confirm password must match")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")


def _encode_google_state(settings: Settings, next_path: str) -> str:
    payload = {
        "next": next_path if next_path.startswith("/") else "/",
        "ts": int(datetime.now(tz=UTC).timestamp()),
    }
    raw_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(raw_payload).decode("ascii").rstrip("=")
    signature = hmac.new(
        settings.auth_session_secret.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def _decode_google_state(settings: Settings, state: str) -> str:
    try:
        payload_b64, signature = state.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Google OAuth state") from exc

    expected_signature = hmac.new(
        settings.auth_session_secret.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=400, detail="Invalid Google OAuth state")

    padding = "=" * (-len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode((payload_b64 + padding).encode("ascii")).decode("utf-8"))
    next_path = payload.get("next")
    return next_path if isinstance(next_path, str) and next_path.startswith("/") else "/"
