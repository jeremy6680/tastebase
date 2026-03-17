# api/dependencies.py

"""
FastAPI dependency: yields a DuckDB connection scoped to a single request.

Each request gets its own connection to avoid concurrent write conflicts.
The connection is always closed after the request completes, whether or not
an exception was raised.

Schema resolution:
  dbt materialises gold models into the `main_gold` schema (DuckDB prefixes
  `main_` to every custom schema name).  The search_path is set to
  `main_gold, main_silver, main_bronze, main` so that SQL queries in the
  routers can reference table names without a schema prefix.
"""

import logging
import os
from collections.abc import Generator

import duckdb
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# DuckDB schema names produced by dbt (dbt prefixes `main_` to custom schemas)
_SEARCH_PATH = "main_gold,main_silver,main_bronze,main"


def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Yield a DuckDB connection for the duration of a single request.

    Reads the database path from the DUCKDB_PATH environment variable.
    Sets the search_path on every new connection so that router queries
    can reference gold-layer tables without a schema prefix.

    Yields:
        duckdb.DuckDBPyConnection: An open connection to the warehouse.

    Raises:
        HTTPException: 503 if DUCKDB_PATH is missing or the file cannot
            be opened.
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
        # Set search_path so unqualified table names resolve to the gold
        # schema first, then silver, bronze, and finally the default schema.
        conn.execute(f"SET search_path = '{_SEARCH_PATH}'")
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
