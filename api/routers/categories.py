# api/routers/categories.py

"""
Category endpoints.

GET  /items/{item_id}/category  — current genre/sub_genre for an item, or null
POST /items/{item_id}/category  — upsert genre + sub_genre (create or replace)
"""

import logging
from datetime import datetime, timezone

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_db
from api.schemas.category import Category, CategoryBatch, CategoryUpsert

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/items", tags=["categories"])
batch_router = APIRouter(prefix="/categories", tags=["categories"])

# DDL executed once at app startup (see api/main.py lifespan)
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS main_gold.mart_item_categories (
    item_id    VARCHAR PRIMARY KEY,
    domain     VARCHAR NOT NULL,
    genre      VARCHAR NOT NULL,
    sub_genre  VARCHAR,
    updated_at TIMESTAMPTZ NOT NULL
)
"""


def ensure_table(db: duckdb.DuckDBPyConnection) -> None:
    """Create mart_item_categories if it does not exist.

    Called once at application startup via the FastAPI lifespan hook.
    Safe to call repeatedly — uses CREATE TABLE IF NOT EXISTS.

    Args:
        db: DuckDB connection.
    """
    db.execute(_CREATE_TABLE_SQL)


# ---------------------------------------------------------------------------
# GET /items/{item_id}/category
# ---------------------------------------------------------------------------


@router.get("/{item_id}/category", response_model=Category | None)
def get_category(
    item_id: str,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> Category | None:
    """Return the current genre/sub_genre for an item, or null if uncategorised.

    Args:
        item_id: SHA256 item identifier.
        db: DuckDB connection injected by FastAPI.

    Returns:
        Category | None: Current category, or None if not yet set.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    _assert_item_exists(item_id, db)

    row = db.execute(
        """
        SELECT item_id, domain, genre, sub_genre, updated_at
        FROM mart_item_categories
        WHERE item_id = ?
        """,
        [item_id],
    ).fetchone()

    if row is None:
        return None

    return Category(
        item_id=row[0],
        domain=row[1],
        genre=row[2],
        sub_genre=row[3],
        updated_at=row[4],
    )


# ---------------------------------------------------------------------------
# POST /items/{item_id}/category
# ---------------------------------------------------------------------------


@router.post("/{item_id}/category", response_model=Category)
def upsert_category(
    item_id: str,
    payload: CategoryUpsert,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> Category:
    """Set or replace the genre/sub_genre for a taste item.

    Uses INSERT OR REPLACE semantics — if a category already exists for
    this item, it is fully replaced (not merged).

    Args:
        item_id: SHA256 item identifier.
        payload: Genre and optional sub_genre values.
        db: DuckDB connection injected by FastAPI.

    Returns:
        Category: The saved category.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    # Fetch item domain — needed to store alongside the category
    row = db.execute(
        "SELECT id, domain FROM mart_unified_tastes WHERE id = ?", [item_id]
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found.")

    domain = row[1]
    now = datetime.now(timezone.utc)

    db.execute(
        """
        INSERT INTO mart_item_categories (item_id, domain, genre, sub_genre, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (item_id) DO UPDATE SET
            genre      = excluded.genre,
            sub_genre  = excluded.sub_genre,
            updated_at = excluded.updated_at
        """,
        [item_id, domain, payload.genre, payload.sub_genre, now],
    )

    return Category(
        item_id=item_id,
        domain=domain,
        genre=payload.genre,
        sub_genre=payload.sub_genre,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# POST /categories/batch
# ---------------------------------------------------------------------------


@batch_router.post("/batch", response_model=list[Category])
def batch_upsert_categories(
    payload: CategoryBatch,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> list[Category]:
    """Apply the same genre/sub_genre to multiple items in one request.

    Items that do not exist in mart_unified_tastes are silently skipped.
    Returns only the categories that were actually saved.

    Args:
        payload: List of item_ids + genre + optional sub_genre.
        db: DuckDB connection injected by FastAPI.

    Returns:
        list[Category]: Saved categories, one per matched item.
    """
    if not payload.item_ids:
        return []

    now = datetime.now(timezone.utc)

    # Resolve which item_ids actually exist and fetch their domains
    placeholders = ", ".join(["?"] * len(payload.item_ids))
    rows = db.execute(
        f"SELECT id, domain FROM mart_unified_tastes WHERE id IN ({placeholders})",
        payload.item_ids,
    ).fetchall()

    if not rows:
        return []

    # Upsert each found item
    saved: list[Category] = []
    for item_id, domain in rows:
        db.execute(
            """
            INSERT INTO mart_item_categories (item_id, domain, genre, sub_genre, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (item_id) DO UPDATE SET
                genre      = excluded.genre,
                sub_genre  = excluded.sub_genre,
                updated_at = excluded.updated_at
            """,
            [item_id, domain, payload.genre, payload.sub_genre, now],
        )
        saved.append(Category(
            item_id=item_id,
            domain=domain,
            genre=payload.genre,
            sub_genre=payload.sub_genre,
            updated_at=now,
        ))

    logger.info(
        "Batch category upsert: %d/%d items saved (genre=%s)",
        len(saved), len(payload.item_ids), payload.genre,
    )
    return saved


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _assert_item_exists(item_id: str, db: duckdb.DuckDBPyConnection) -> None:
    """Raise 404 if the item does not exist in mart_unified_tastes.

    Args:
        item_id: SHA256 item identifier.
        db: DuckDB connection.

    Raises:
        HTTPException: 404 if the item is not found.
    """
    row = db.execute(
        "SELECT id FROM mart_unified_tastes WHERE id = ?", [item_id]
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found.")
