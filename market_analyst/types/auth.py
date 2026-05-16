from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    first_name: str
    last_name: str
    email: str
    mobile_number: str
    gender: str
    dob: date


@dataclass(frozen=True)
class GoogleUserProfile:
    subject: str
    email: str
    email_verified: bool
    given_name: str
    family_name: str
    full_name: str


@dataclass(frozen=True)
class GoogleTokenExchangeResult:
    access_token: str
    id_token: str | None = None
