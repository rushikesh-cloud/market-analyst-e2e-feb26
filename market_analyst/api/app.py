from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from market_analyst.api.dependencies import get_settings, require_authenticated_user
from market_analyst.api.routes import auth, companies, documents, supervisor_runs


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Market Analyst API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router, prefix="/api")
    app.include_router(companies.router, prefix="/api", dependencies=[Depends(require_authenticated_user)])
    app.include_router(documents.router, prefix="/api", dependencies=[Depends(require_authenticated_user)])
    app.include_router(supervisor_runs.router, prefix="/api", dependencies=[Depends(require_authenticated_user)])

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
