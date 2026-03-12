# api/main.py

"""
TasteBase FastAPI application.

Entry point for the API layer. Registers all routers and configures:
- CORS (permissive in development, restricted in production)
- Structured logging
- OpenAPI metadata
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import ingestion, items, ratings, stats

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown hooks
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan context manager.

    Runs on startup: validates that DUCKDB_PATH is set and logs the
    database location. Does not open a persistent connection — connections
    are per-request via get_db().

    Args:
        app: The FastAPI application instance.

    Yields:
        None
    """
    db_path = os.getenv("DUCKDB_PATH")
    if not db_path:
        logger.warning(
            "DUCKDB_PATH is not set. All database endpoints will return 503."
        )
    else:
        logger.info("TasteBase API starting. DuckDB path: %s", db_path)

    yield

    logger.info("TasteBase API shutting down.")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance.
    """
    app = FastAPI(
        title="TasteBase API",
        description=(
            "Personal cultural taste warehouse API. "
            "Exposes unified taste data (music, books, manga, movies, series, anime) "
            "stored in DuckDB via a medallion architecture."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow all origins in development, restrict in production
    app_env = os.getenv("APP_ENV", "development")
    allowed_origins = (
        ["*"]
        if app_env == "development"
        else [os.getenv("FRONTEND_URL", "http://localhost:3000")]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(items.router)
    app.include_router(ratings.router)
    app.include_router(stats.router)
    app.include_router(ingestion.router)

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        """Liveness probe. Returns 200 if the API is running."""
        return {"status": "ok"}

    return app


app = create_app()