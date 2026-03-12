# api/dependencies.py

"""
FastAPI dependency: yields a DuckDB connection scoped to a single request.

Each request gets its own connection to avoid concurrent write conflicts.
The connection is always closed after the request completes, whether or not
an exception was raised.
"""

import logging
import os
from collections.abc import Generator

import duckdb
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Yield a DuckDB connection for the duration of a single request.

    Reads the database path from the DUCKDB_PATH environment variable.
    Raises a 503 if the variable is missing or the file cannot be opened.

    Yields:
        duckdb.DuckDBPyConnection: An open connection to the warehouse.

    Raises:
        HTTPException: 503 if the database cannot be reached.
    """
    db_path = os.getenv("DUCKDB_PATH")
    if not db_path:
        raise HTTPException(
            status_code=503,
            detail="DUCKDB_PATH is not set. Check your environment configuration.",
        )

    conn: duckdb.DuckDBPyConnection | None = None
    try:
        conn = duckdb.connect(db_path, read_only=False)
        yield conn
    except duckdb.IOException as exc:
        logger.error("Failed to open DuckDB at %s: %s", db_path, exc)
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc
    finally:
        if conn is not None:
            conn.close()