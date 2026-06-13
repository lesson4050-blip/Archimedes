"""Archimedes — FastAPI application entry point.

Initialises the ASGI app, attaches middleware, and wires up the
lifespan context manager for startup/shutdown hooks.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks.

    Startup:
        Future phases will initialise DB connections, ChromaDB client,
        and the WebSocket hub here.

    Shutdown:
        Graceful cleanup of resources.
    """
    # ── Startup ─────────────────────────────────────────────
    # TODO(phase-1): init SQLite, ChromaDB, WS hub
    yield
    # ── Shutdown ────────────────────────────────────────────
    # TODO(phase-1): close DB pools, flush logs


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Archimedes",
        description="Autonomous AI agent platform",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # ── Middleware ───────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ─────────────────────────────────────────────
    app.include_router(router)

    return app


app: FastAPI = create_app()
