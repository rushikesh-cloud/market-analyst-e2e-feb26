from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from market_analyst.api import dependencies
from market_analyst.api.app import app
from market_analyst.api.routes import auth as auth_route
from market_analyst.config.settings import Settings


NOW = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)


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
        frontend_app_url="http://localhost:3000",
        auth_session_secret="test-secret",
    )


def _user_row() -> dict[str, object]:
    return {
        "id": "a0d15fcb-8561-4e20-b399-6819d0d08484",
        "first_name": "Ava",
        "last_name": "Analyst",
        "email": "ava@example.com",
        "mobile_number": "9876543210",
        "gender": "female",
        "dob": date(1997, 4, 2),
        "created_at": NOW,
        "updated_at": NOW,
    }


def test_register_sets_cookie_and_returns_user(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    monkeypatch.setattr(auth_route, "register_user", lambda *args, **kwargs: (_user_row(), "session-token", NOW))

    client = TestClient(app)
    response = client.post(
        "/api/auth/register",
        json={
            "firstName": "Ava",
            "lastName": "Analyst",
            "email": "ava@example.com",
            "mobileNumber": "9876543210",
            "gender": "female",
            "dob": "1997-04-02",
            "password": "password123",
            "confirmPassword": "password123",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    assert response.json()["email"] == "ava@example.com"
    assert settings.auth_session_cookie_name in response.headers["set-cookie"]


def test_login_sets_cookie(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    monkeypatch.setattr(auth_route, "login_user", lambda *args, **kwargs: (_user_row(), "session-token", NOW))

    client = TestClient(app)
    response = client.post("/api/auth/login", json={"email": "ava@example.com", "password": "password123"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert settings.auth_session_cookie_name in response.headers["set-cookie"]


def test_me_requires_authentication(tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    app.dependency_overrides[dependencies.get_current_user] = lambda: None

    client = TestClient(app)
    response = client.get("/api/auth/me")

    app.dependency_overrides.clear()
    assert response.status_code == 401


def test_me_returns_authenticated_user(tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    app.dependency_overrides[dependencies.get_current_user] = _user_row

    client = TestClient(app)
    response = client.get("/api/auth/me")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["firstName"] == "Ava"


def test_logout_clears_cookie(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    captured: dict[str, object] = {}
    monkeypatch.setattr(auth_route, "logout_user", lambda passed_settings, token: captured.setdefault("token", token))

    client = TestClient(app)
    response = client.post("/api/auth/logout", cookies={settings.auth_session_cookie_name: "session-token"})

    app.dependency_overrides.clear()
    assert response.status_code == 204
    assert captured["token"] == "session-token"
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_google_start_redirects_to_provider(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    monkeypatch.setattr(auth_route, "create_google_authorization_redirect", lambda passed_settings, next: "https://accounts.google.com/o/oauth2/auth?state=abc")

    client = TestClient(app)
    response = client.get("/api/auth/google/start?next=%2Fdocuments", follow_redirects=False)

    app.dependency_overrides.clear()
    assert response.status_code == 302
    assert response.headers["location"].startswith("https://accounts.google.com/")


def test_google_callback_sets_cookie_and_redirects(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[dependencies.get_settings] = lambda: settings
    monkeypatch.setattr(
        auth_route,
        "authenticate_with_google",
        lambda passed_settings, code, state: (_user_row(), "session-token", NOW, "/documents"),
    )

    client = TestClient(app)
    response = client.get("/api/auth/google/callback?code=sample&state=opaque", follow_redirects=False)

    app.dependency_overrides.clear()
    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost:3000/documents"
    assert settings.auth_session_cookie_name in response.headers["set-cookie"]
