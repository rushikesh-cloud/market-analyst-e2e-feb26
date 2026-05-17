from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_env_file(path: Path | None = None) -> None:
    """Load a simple .env file without requiring python-dotenv."""

    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    database_host: str
    database_port: int
    database_name: str
    database_user: str
    database_password: str
    document_intelligence_endpoint: str
    document_intelligence_key: str
    azure_openai_endpoint: str
    azure_openai_key: str
    azure_openai_version: str
    azure_openai_chat_deployment: str
    azure_openai_embedding_deployment: str
    tavily_api_key: str = ""
    azure_ai_project_endpoint: str = ""
    document_intelligence_connection_verify: str = ""
    opik_api_key: str = ""
    opik_workspace: str = ""
    opik_project_name: str = "market-analyst"
    opik_url_override: str = ""
    frontend_app_url: str = "http://localhost:3000"
    auth_cookie_secure: bool = False
    auth_session_cookie_name: str = "market_analyst_session"
    auth_session_ttl_hours: int = 336
    auth_session_secret: str = "market-analyst-dev-session-secret"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    vector_collection_name: str = "fundamental_report_chunks"
    upload_dir: Path = PROJECT_ROOT / "uploads" / "documents"
    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")

    @property
    def database_url(self) -> str:
        user = quote_plus(self.database_user)
        password = quote_plus(self.database_password)
        host = self.database_host
        db_name = quote_plus(self.database_name)
        return f"postgresql+psycopg://{user}:{password}@{host}:{self.database_port}/{db_name}"

    @property
    def psycopg_dsn(self) -> str:
        user = quote_plus(self.database_user)
        password = quote_plus(self.database_password)
        host = self.database_host
        db_name = quote_plus(self.database_name)
        return f"postgresql://{user}:{password}@{host}:{self.database_port}/{db_name}"

    def require_database(self) -> None:
        missing = [
            name
            for name, value in {
                "DATABASE_HOST": self.database_host,
                "DATABASE_NAME": self.database_name,
                "DATABASE_USER": self.database_user,
                "DATABASE_PASSWORD": self.database_password,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing database settings: {', '.join(missing)}")

    def require_document_intelligence(self) -> None:
        missing = [
            name
            for name, value in {
                "DOCUMENT_INTELLIGENCE_ENDPOINT": self.document_intelligence_endpoint,
                "DOCUMENT_INTELLIGENCE_KEY": self.document_intelligence_key,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing Azure Document Intelligence settings: {', '.join(missing)}")

    def require_embeddings(self) -> None:
        missing = [
            name
            for name, value in {
                "AZURE_OPENAI_ENDPOINT": self.azure_openai_endpoint,
                "AZURE_OPENAI_KEY": self.azure_openai_key,
                "AZURE_OPENAI_VERSION": self.azure_openai_version,
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": self.azure_openai_embedding_deployment,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing Azure OpenAI embedding settings: {', '.join(missing)}")

    def require_chat_model(self) -> None:
        missing = [
            name
            for name, value in {
                "AZURE_OPENAI_ENDPOINT": self.azure_openai_endpoint,
                "AZURE_OPENAI_KEY": self.azure_openai_key,
                "AZURE_OPENAI_VERSION": self.azure_openai_version,
                "AZURE_OPENAI_DEPLOYMENT": self.azure_openai_chat_deployment,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing Azure OpenAI chat settings: {', '.join(missing)}")

    def require_tavily(self) -> None:
        if not self.tavily_api_key:
            raise ValueError("Missing Tavily setting: TAVILY_API_KEY")

    def require_auth(self) -> None:
        missing = [
            name
            for name, value in {
                "AUTH_SESSION_SECRET": self.auth_session_secret,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing auth settings: {', '.join(missing)}")

    def require_google_oauth(self) -> None:
        missing = [
            name
            for name, value in {
                "GOOGLE_CLIENT_ID": self.google_client_id,
                "GOOGLE_CLIENT_SECRET": self.google_client_secret,
                "GOOGLE_OAUTH_REDIRECT_URI": self.google_oauth_redirect_uri,
                "AUTH_SESSION_SECRET": self.auth_session_secret,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing Google OAuth settings: {', '.join(missing)}")


def load_settings() -> Settings:
    load_env_file()
    frontend_app_url = os.getenv("FRONTEND_APP_URL", "http://localhost:3000").rstrip("/")
    auth_cookie_secure = os.getenv("AUTH_COOKIE_SECURE")
    if auth_cookie_secure is None:
        auth_cookie_secure_value = frontend_app_url.startswith("https://")
    else:
        auth_cookie_secure_value = auth_cookie_secure.strip().lower() in {"1", "true", "yes", "on"}
    return Settings(
        database_host=os.getenv("DATABASE_HOST", "localhost"),
        database_port=int(os.getenv("DATABASE_PORT", "5432")),
        database_name=os.getenv("DATABASE_NAME", ""),
        database_user=os.getenv("DATABASE_USER", ""),
        database_password=os.getenv("DATABASE_PASSWORD", ""),
        document_intelligence_endpoint=os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT", ""),
        document_intelligence_key=os.getenv("DOCUMENT_INTELLIGENCE_KEY", ""),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        azure_openai_key=os.getenv("AZURE_OPENAI_KEY", ""),
        azure_openai_version=os.getenv("AZURE_OPENAI_VERSION", "2024-02-01"),
        azure_openai_chat_deployment=(
            os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
            or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "")
            or os.getenv("AZURE_OPENAI_MODEL_DEPLOYMENT", "")
        ),
        azure_openai_embedding_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", ""),
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        azure_ai_project_endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT", ""),
        document_intelligence_connection_verify=os.getenv("DOCUMENT_INTELLIGENCE_CONNECTION_VERIFY", ""),
        opik_api_key=os.getenv("OPIK_API_KEY", ""),
        opik_workspace=os.getenv("OPIK_WORKSPACE", ""),
        opik_project_name=os.getenv("OPIK_PROJECT_NAME", "market-analyst"),
        opik_url_override=os.getenv("OPIK_URL_OVERRIDE", ""),
        frontend_app_url=frontend_app_url,
        auth_cookie_secure=auth_cookie_secure_value,
        auth_session_cookie_name=os.getenv("AUTH_SESSION_COOKIE_NAME", "market_analyst_session"),
        auth_session_ttl_hours=int(os.getenv("AUTH_SESSION_TTL_HOURS", "336")),
        auth_session_secret=os.getenv("AUTH_SESSION_SECRET", "market-analyst-dev-session-secret"),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        google_oauth_redirect_uri=os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback"),
        vector_collection_name=os.getenv("VECTOR_COLLECTION_NAME", "fundamental_report_chunks"),
        upload_dir=Path(os.getenv("UPLOAD_DIR", str(PROJECT_ROOT / "uploads" / "documents"))),
        cors_origins=tuple(
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
            if origin.strip()
        ),
    )
