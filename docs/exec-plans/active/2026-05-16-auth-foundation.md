# Auth Foundation

## Goal

Add the first protected auth boundary to the Market Analyst app with local email/password auth plus Google OAuth, backed by FastAPI and PostgreSQL instead of browser-only storage.

## Scope

- Add backend user, auth identity, and session persistence inside the existing psycopg project schema.
- Expose auth routes for register, login, logout, current user lookup, Google OAuth start, and Google OAuth callback.
- Protect the existing company, document, workflow, and run-detail app surfaces behind auth.
- Add minimal standalone login and register pages in the Next.js frontend.
- Update `specs.md` and `docs/generated/db-schema.md` to describe the new capability and planned data model.

## Verification

- Run backend auth tests plus existing API route tests.
- Run the frontend production build.
- Confirm unauthenticated app access redirects to `/login` and authenticated auth-page access redirects to `/`.
