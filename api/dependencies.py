# api/dependencies.py

"""
FastAPI dependencies: DuckDB connections scoped to a single request.

Two flavours:
  get_db       — read-only connection (safe for concurrent requests)
  get_db_write — read-write connection (used only by write endpoints)

DuckDB allows multiple concurrent readers but only one writer at a time.
Using read-only connections for all read endpoints eliminates lock conflicts
with the ingestion pipeline, which needs a write connection.
"""

import logging
import os
from collections.abc import Generator

import duckdb
from fastapi import HTTPException

logger = logging.getLogger(__name__)

_SEARCH_PATH = "main_gold,main_silver,main_bronze,main"


def _open_connection(read_only: bool) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection with the correct search_path.

    Args:
        read_only: Whether to open in read-only mode.

    Returns:
        duckdb.DuckDBPyConnection: Open connection.

    Raises:
        HTTPException: 503 if DUCKDB_PATH is missing or the file cannot be opened.
    """
    db_path = os.getenv("DUCKDB_PATH")
    if not db_path:
        raise HTTPException(
            status_code=503,
            detail="DUCKDB_PATH is not set. Check your environment configuration.",
        )
    try:
        conn = duckdb.connect(db_path, read_only=read_only)
        conn.execute(f"SET search_path = '{_SEARCH_PATH}'")
        return conn
    except duckdb.IOException as exc:
        logger.error("Failed to open DuckDB at %s: %s", db_path, exc)
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc


def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Yield a read-only DuckDB connection for the duration of a single request.

    Read-only mode allows concurrent readers and does not block the ingestion
    pipeline from acquiring a write lock.

    Yields:
        duckdb.DuckDBPyConnection: Read-only connection to the warehouse.

    Raises:
        HTTPException: 503 if DUCKDB_PATH is missing or the file cannot be opened.
    """
    conn = _open_connection(read_only=True)
    try:
        yield conn
    finally:
        conn.close()


def get_db_write() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Yield a read-write DuckDB connection for the duration of a single request.

    Use only for endpoints that write to the database (ratings, categories).
    Holds an exclusive write lock for the duration of the request.

    Yields:
        duckdb.DuckDBPyConnection: Read-write connection to the warehouse.

    Raises:
        HTTPException: 503 if DUCKDB_PATH is missing or the file cannot be opened.
    """
    conn = _open_connection(read_only=False)
    try:
        yield conn
    finally:
        conn.close()