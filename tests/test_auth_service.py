from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi import HTTPException

from market_analyst.config.settings import Settings
from market_analyst.services import auth as auth_service
from market_analyst.types.auth import GoogleUserProfile


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_host="localhost",
        database_port=5432,
        database_name="test",
        database_user="test",
        database_password="test",
        document_intelligence_endpoint="",
        document_intelligence_key="",
        azure_openai_endpoint="",
        azure_openai_key="",
        azure_openai_version="2024-02-01",
        azure_openai_chat_deployment="",
        azure_openai_embedding_deployment="",
        tavily_api_key="",
        upload_dir=tmp_path / "uploads",
        auth_session_secret="test-secret",
    )


def test_hash_password_and_verify() -> None:
    salt, password_hash = auth_service.hash_password("password123")
    assert password_hash != "password123"
    assert auth_service.verify_password(password="password123", salt=salt, password_hash=password_hash) is True
    assert auth_service.verify_password(password="wrong", salt=salt, password_hash=password_hash) is False


def test_register_rejects_duplicate_email(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(auth_service, "get_user_by_email", lambda passed_settings, email: {"id": "existing-user"})

    with pytest.raises(HTTPException) as exc_info:
        auth_service.register_user(
            settings,
            first_name="Ava",
            last_name="Analyst",
            email="ava@example.com",
            mobile_number="9876543210",
            gender="female",
            dob=date(1997, 4, 2),
            password="password123",
            confirm_password="password123",
        )

    assert exc_info.value.status_code == 409


def test_login_rejects_invalid_password(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        auth_service,
        "get_local_identity_by_email",
        lambda passed_settings, email: {"password_salt": "c2FsdA==", "password_hash": "aGFzaA=="},
    )
    monkeypatch.setattr(auth_service, "verify_password", lambda **kwargs: False)

    with pytest.raises(HTTPException) as exc_info:
        auth_service.login_user(settings, email="ava@example.com", password="wrong")

    assert exc_info.value.status_code == 401


def test_google_callback_creates_new_account_when_email_is_new(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    profile = GoogleUserProfile(
        subject="google-subject",
        email="ava@example.com",
        email_verified=True,
        given_name="Ava",
        family_name="Analyst",
        full_name="Ava Analyst",
    )
    created_users: list[dict[str, object]] = []
    created_identities: list[dict[str, object]] = []
    monkeypatch.setattr(auth_service, "get_auth_identity", lambda passed_settings, provider, subject: None)
    monkeypatch.setattr(auth_service, "get_user_by_email", lambda passed_settings, email: None)
    monkeypatch.setattr(
        auth_service,
        "create_user",
        lambda passed_settings, **kwargs: created_users.append({"id": "user-1", **kwargs}) or {"id": "user-1", **kwargs},
    )
    monkeypatch.setattr(
        auth_service,
        "create_auth_identity",
        lambda passed_settings, **kwargs: created_identities.append(kwargs) or kwargs,
    )

    user = auth_service._find_or_create_google_user(settings, profile)

    assert user["id"] == "user-1"
    assert created_users[0]["email"] == "ava@example.com"
    assert created_identities[0]["provider"] == "google"


def test_google_callback_auto_links_existing_local_account(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    profile = GoogleUserProfile(
        subject="google-subject",
        email="ava@example.com",
        email_verified=True,
        given_name="Ava",
        family_name="Analyst",
        full_name="Ava Analyst",
    )
    local_user = {
        "id": "existing-user",
        "first_name": "Ava",
        "last_name": "Analyst",
        "email": "ava@example.com",
        "mobile_number": "9876543210",
        "gender": "female",
        "dob": date(1997, 4, 2),
        "created_at": datetime(2026, 5, 16, tzinfo=UTC),
        "updated_at": datetime(2026, 5, 16, tzinfo=UTC),
    }
    created_identities: list[dict[str, object]] = []
    monkeypatch.setattr(auth_service, "get_auth_identity", lambda passed_settings, provider, subject: None)
    monkeypatch.setattr(auth_service, "get_user_by_email", lambda passed_settings, email: local_user)
    monkeypatch.setattr(auth_service, "create_user", lambda passed_settings, **kwargs: pytest.fail("create_user should not be called"))
    monkeypatch.setattr(
        auth_service,
        "create_auth_identity",
        lambda passed_settings, **kwargs: created_identities.append(kwargs) or kwargs,
    )

    user = auth_service._find_or_create_google_user(settings, profile)

    assert user["id"] == "existing-user"
    assert created_identities[0]["user_id"] == "existing-user"
