"""FastAPI application factory for the Mini Lead Assistant."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import VERSION, get_cors_origins
from .routers import lead


def create_app() -> FastAPI:
    app = FastAPI(title="Mini Lead Assistant", version=VERSION)

    # CORS for local dev (Vite dev server on a different port). The Vite proxy
    # also routes /api, so this mainly covers direct browser calls. Defaults to
    # "*"; set CORS_ORIGINS to lock it down in a real deployment.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(lead.router)
    return app


app = create_app()
