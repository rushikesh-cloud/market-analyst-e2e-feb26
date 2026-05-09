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
    azure_openai_endpoint: str
    azure_openai_key: str
    azure_openai_version: str
    azure_openai_embedding_deployment: str
    vector_collection_name: str = "fundamental_report_chunks"

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


def load_settings() -> Settings:
    load_env_file()
    return Settings(
        database_host=os.getenv("DATABASE_HOST", "localhost"),
        database_port=int(os.getenv("DATABASE_PORT", "5432")),
        database_name=os.getenv("DATABASE_NAME", ""),
        database_user=os.getenv("DATABASE_USER", ""),
        database_password=os.getenv("DATABASE_PASSWORD", ""),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        azure_openai_key=os.getenv("AZURE_OPENAI_KEY", ""),
        azure_openai_version=os.getenv("AZURE_OPENAI_VERSION", "2024-02-01"),
        azure_openai_embedding_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", ""),
        vector_collection_name=os.getenv("VECTOR_COLLECTION_NAME", "fundamental_report_chunks"),
    )
