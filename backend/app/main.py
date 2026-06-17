"""FastAPI application factory for the Mini Lead Assistant."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import lead


def create_app() -> FastAPI:
    app = FastAPI(title="Mini Lead Assistant", version="1.0.0")

    # Permissive CORS for local dev (Vite dev server on a different port). The
    # Vite proxy also routes /api, so this mainly covers direct browser calls.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(lead.router)
    return app


app = create_app()
