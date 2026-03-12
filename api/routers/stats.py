# api/routers/stats.py

"""
Read-only statistics endpoints for the dashboard.

GET /stats/counts        — item count per domain
GET /stats/top-rated     — top-rated items, filterable by domain
GET /stats/taste-profile — aggregate taste profile (genres, decades, creators)
GET /stats/recent        — recently added items
"""

import logging

import duckdb
from fastapi import APIRouter, Depends, Query

from api.dependencies import get_db
from api.schemas.item import TasteItemSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stats", tags=["stats"])


# ---------------------------------------------------------------------------
# GET /stats/counts
# ---------------------------------------------------------------------------


@router.get("/counts")
def get_counts(
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> dict[str, int]:
    """Return the number of items per domain.

    Args:
        db: DuckDB connection injected by FastAPI.

    Returns:
        dict[str, int]: Domain name → item count.
    """
    rows = db.execute(
        "SELECT domain, COUNT(*) FROM mart_unified_tastes GROUP BY domain ORDER BY domain"
    ).fetchall()
    return {row[0]: row[1] for row in rows}


# ---------------------------------------------------------------------------
# GET /stats/top-rated
# ---------------------------------------------------------------------------


@router.get("/top-rated", response_model=list[TasteItemSummary])
def get_top_rated(
    domain: str | None = Query(None, description="Filter by domain"),
    limit: int = Query(10, ge=1, le=100),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> list[TasteItemSummary]:
    """Return the highest-rated items, optionally filtered by domain.

    Items are sorted by rating DESC, then title ASC as a tiebreaker.

    Args:
        domain: Optional domain filter.
        limit: Maximum number of results (1–100, default 10).
        db: DuckDB connection injected by FastAPI.

    Returns:
        list[TasteItemSummary]: Top-rated items.
    """
    params: list = []
    domain_filter = ""
    if domain:
        domain_filter = "AND t.domain = ?"
        params.append(domain)

    rows = db.execute(
        f"""
        SELECT t.id, t.domain, t.title, t.creator, t.year, r.rating, t.status
        FROM mart_unified_tastes t
        JOIN mart_ratings r ON t.id = r.item_id
        WHERE r.rating IS NOT NULL {domain_filter}
        ORDER BY r.rating DESC, t.title ASC
        LIMIT ?
        """,
        params + [limit],
    ).fetchall()

    return [
        TasteItemSummary(
            id=row[0], domain=row[1], title=row[2],
            creator=row[3], year=row[4], rating=row[5], status=row[6],
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# GET /stats/taste-profile
# ---------------------------------------------------------------------------


@router.get("/taste-profile")
def get_taste_profile(
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> dict:
    """Return aggregate taste profile data from mart_taste_profile.

    Args:
        db: DuckDB connection injected by FastAPI.

    Returns:
        dict: Rows from mart_taste_profile as a list of dicts.
    """
    rows = db.execute("SELECT * FROM mart_taste_profile").fetchall()
    description = db.description  # column names
    columns = [col[0] for col in description]
    return {"profile": [dict(zip(columns, row)) for row in rows]}


# ---------------------------------------------------------------------------
# GET /stats/recent
# ---------------------------------------------------------------------------


@router.get("/recent", response_model=list[TasteItemSummary])
def get_recent(
    limit: int = Query(20, ge=1, le=100),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> list[TasteItemSummary]:
    """Return the most recently added items across all domains.

    Args:
        limit: Maximum number of results (1–100, default 20).
        db: DuckDB connection injected by FastAPI.

    Returns:
        list[TasteItemSummary]: Recently added items, newest first.
    """
    rows = db.execute(
        """
        SELECT t.id, t.domain, t.title, t.creator, t.year, r.rating, t.status
        FROM mart_unified_tastes t
        LEFT JOIN mart_ratings r ON t.id = r.item_id
        ORDER BY t.date_added DESC NULLS LAST
        LIMIT ?
        """,
        [limit],
    ).fetchall()

    return [
        TasteItemSummary(
            id=row[0], domain=row[1], title=row[2],
            creator=row[3], year=row[4], rating=row[5], status=row[6],
        )
        for row in rows
    ]