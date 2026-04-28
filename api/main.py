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

from dotenv import load_dotenv

# Load .env from the project root (two levels up from api/main.py)
# Must run before any os.getenv() call, including at import time in routers.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import categories, ingestion, items, ratings, stats
from api.routers.categories import batch_router as categories_batch_router
from api.routers.categories import ensure_table

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
        # ensure_table removed from startup — opening a write connection here
        # conflicts with read_only=True connections from get_db() (DEC-037).
        # mart_item_categories is created lazily on first write via categories router.
        logger.info("API ready. mart_item_categories will be created on first write.")

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

    if app_env == "development":
        allowed_origins = ["*"]
    else:
        # Comma-separated list of allowed origins in production
        frontend_url = os.getenv("FRONTEND_URL", "")
        agent_url = os.getenv("TASTEBASE_AGENT_URL", "")
        allowed_origins = [
            origin.strip()
            for origin in [frontend_url, agent_url]
            if origin.strip()
        ]

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
    app.include_router(categories.router)
    app.include_router(categories_batch_router)
    app.include_router(stats.router)
    app.include_router(ingestion.router)

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        """Liveness probe. Returns 200 if the API is running."""
        return {"status": "ok"}

    return app


app = create_app()