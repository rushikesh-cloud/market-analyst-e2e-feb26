from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from uuid import UUID
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from market_analyst.config.settings import Settings
from market_analyst.repositories.vector_db import ensure_project_schema


def get_user_by_email(settings: Settings, email: str) -> dict[str, object] | None:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, first_name, last_name, email, mobile_number, gender, dob, created_at, updated_at
                FROM users
                WHERE email = %s
                """,
                (email.strip().lower(),),
            )
            row = cur.fetchone()
    return _serialize_user_row(row) if row else None


def get_user_by_id(settings: Settings, user_id: str) -> dict[str, object] | None:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, first_name, last_name, email, mobile_number, gender, dob, created_at, updated_at
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
    return _serialize_user_row(row) if row else None


def create_user(
    settings: Settings,
    *,
    first_name: str,
    last_name: str,
    email: str,
    mobile_number: str,
    gender: str,
    dob: date,
) -> dict[str, object]:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, first_name, last_name, email, mobile_number, gender, dob)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, first_name, last_name, email, mobile_number, gender, dob, created_at, updated_at
                """,
                (
                    str(uuid4()),
                    first_name.strip(),
                    last_name.strip(),
                    email.strip().lower(),
                    mobile_number.strip(),
                    gender.strip().lower(),
                    dob,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    if row is None:
        raise RuntimeError("Failed to create auth user")
    return _serialize_user_row(row)


def get_auth_identity(settings: Settings, provider: str, provider_subject: str) -> dict[str, object] | None:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, provider, provider_subject, email, password_salt, password_hash, created_at, updated_at
                FROM auth_identities
                WHERE provider = %s AND provider_subject = %s
                """,
                (provider, provider_subject),
            )
            row = cur.fetchone()
    return _serialize_identity_row(row) if row else None


def create_auth_identity(
    settings: Settings,
    *,
    user_id: str,
    provider: str,
    provider_subject: str,
    email: str,
    password_salt: str | None = None,
    password_hash: str | None = None,
) -> dict[str, object]:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth_identities (
                    id,
                    user_id,
                    provider,
                    provider_subject,
                    email,
                    password_salt,
                    password_hash
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, user_id, provider, provider_subject, email, password_salt, password_hash, created_at, updated_at
                """,
                (
                    str(uuid4()),
                    user_id,
                    provider,
                    provider_subject,
                    email.strip().lower(),
                    password_salt,
                    password_hash,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    if row is None:
        raise RuntimeError("Failed to create auth identity")
    return _serialize_identity_row(row)


def get_local_identity_by_email(settings: Settings, email: str) -> dict[str, object] | None:
    return get_auth_identity(settings, "local", email.strip().lower())


def list_auth_identities_for_user(settings: Settings, user_id: str) -> list[dict[str, object]]:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, provider, provider_subject, email, password_salt, password_hash, created_at, updated_at
                FROM auth_identities
                WHERE user_id = %s
                ORDER BY created_at ASC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
    return [_serialize_identity_row(row) for row in rows]


def create_user_session(
    settings: Settings,
    *,
    user_id: str,
    token_hash: str,
    expires_at: datetime,
) -> dict[str, object]:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_sessions (id, user_id, token_hash, expires_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id, user_id, token_hash, expires_at, created_at
                """,
                (str(uuid4()), user_id, token_hash, expires_at),
            )
            row = cur.fetchone()
        conn.commit()
    if row is None:
        raise RuntimeError("Failed to create auth session")
    return _serialize_mapping(row)


def delete_user_session(settings: Settings, token_hash: str) -> None:
    ensure_project_schema(settings)
    with psycopg.connect(settings.psycopg_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_sessions WHERE token_hash = %s", (token_hash,))
        conn.commit()


def get_user_by_session_token(settings: Settings, session_token: str) -> dict[str, object] | None:
    ensure_project_schema(settings)
    token_hash = _hash_session_token(session_token)
    with psycopg.connect(settings.psycopg_dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    users.id,
                    users.first_name,
                    users.last_name,
                    users.email,
                    users.mobile_number,
                    users.gender,
                    users.dob,
                    users.created_at,
                    users.updated_at
                FROM user_sessions
                JOIN users ON users.id = user_sessions.user_id
                WHERE user_sessions.token_hash = %s
                  AND user_sessions.expires_at > now()
                """,
                (token_hash,),
            )
            row = cur.fetchone()
    return _serialize_user_row(row) if row else None


def _serialize_user_row(row: Mapping[str, object]) -> dict[str, object]:
    serialized = _serialize_mapping(row)
    if isinstance(serialized.get("dob"), datetime):
        serialized["dob"] = serialized["dob"].date()
    return serialized


def _serialize_identity_row(row: Mapping[str, object]) -> dict[str, object]:
    return _serialize_mapping(row)


def _serialize_mapping(row: Mapping[str, object]) -> dict[str, object]:
    serialized = dict(row)
    for key, value in list(serialized.items()):
        if isinstance(value, UUID):
            serialized[key] = str(value)
        elif isinstance(value, datetime):
            serialized[key] = value.astimezone(UTC)
    return serialized


def _hash_session_token(session_token: str) -> str:
    import hashlib

    return hashlib.sha256(session_token.encode("utf-8")).hexdigest()
