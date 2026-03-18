# api/routers/items.py

"""
CRUD endpoints for taste items.

GET  /items                — paginated list, filterable by domain / status / rating / title
GET  /items/{item_id}      — single item with current rating
POST /items                — create a new item
PATCH /items/{item_id}     — partial update
DELETE /items/{item_id}    — soft-delete (sets a deleted_at flag) — NOT IMPLEMENTED YET
                             Hard delete is intentionally excluded from v1.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_db
from api.schemas.item import (
    PaginatedItems,
    TasteItem,
    TasteItemCreate,
    TasteItemSummary,
    TasteItemUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/items", tags=["items"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_item_id(domain: str, source: str, source_id: str | None, title: str) -> str:
    """Generate a stable SHA256 ID for a taste item.

    Mirrors the logic used in mart_unified_tastes.sql so that manually
    created items can be matched against warehouse-generated ones.

    Args:
        domain: Content domain (music, book, etc.).
        source: Source identifier (musicbuddy, spotify, etc.).
        source_id: Original ID in the source system, or None.
        title: Item title (used as fallback when source_id is None).

    Returns:
        str: 64-character hex SHA256 digest.
    """
    key = f"{domain}:{source}:{source_id or title}"
    return hashlib.sha256(key.encode()).hexdigest()


def _row_to_item(row: tuple) -> TasteItem:
    """Map a DuckDB row tuple from the items query to a TasteItem.

    Column order must match the SELECT in get_item().

    Args:
        row: Raw DuckDB result row.

    Returns:
        TasteItem: Populated schema instance.
    """
    (
        id_,
        domain,
        source,
        source_id,
        title,
        creator,
        year,
        genres,
        cover_url,
        external_ids_raw,
        status,
        date_added,
        date_consumed,
        created_at,
        updated_at,
        rating,
    ) = row

    return TasteItem(
        id=id_,
        domain=domain,
        source=source,
        source_id=source_id,
        title=title,
        creator=creator,
        year=year,
        genres=genres or [],
        cover_url=cover_url,
        external_ids=json.loads(external_ids_raw) if isinstance(external_ids_raw, str) else (external_ids_raw or {}),
        status=status,
        date_added=date_added,
        date_consumed=date_consumed,
        created_at=created_at,
        updated_at=updated_at,
        rating=rating,
    )


# ---------------------------------------------------------------------------
# GET /items
# ---------------------------------------------------------------------------


# Valid sort columns mapped to their SQL expressions (whitelist against injection)
_SORT_COLUMNS: dict[str, str] = {
    "title":   "t.title",
    "creator": "t.creator",
    "year":    "t.year",
    "rating":  "r.rating",
}


@router.get("/", response_model=PaginatedItems)
def list_items(
    domain: str | None = Query(None, description="Filter by domain"),
    status: str | None = Query(None, description="Filter by status"),
    min_rating: int | None = Query(None, ge=1, le=5, description="Minimum rating"),
    search: str | None = Query(None, description="Search title or creator (case-insensitive, partial match)"),
    decade: int | None = Query(None, description="Filter by decade start year (e.g. 1990 for the 1990s)"),
    genre: str | None = Query(None, description="Filter by genre (from mart_item_categories)"),
    sub_genre: str | None = Query(None, description="Filter by sub_genre (requires genre)"),
    sort_by: str = Query("title", description="Sort field: title | creator | year | rating"),
    sort_dir: str = Query("asc", description="Sort direction: asc | desc"),
    limit: int | None = Query(None, ge=1, le=200, description="Max results (used by agent tools, overrides page_size)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> PaginatedItems:
    """Return a paginated list of taste items with optional filters and sorting.

    Args:
        domain: Optional domain filter (music, book, manga, movie, series, anime).
        status: Optional status filter.
        min_rating: Optional minimum rating filter (1–5).
        search: Optional search query matched against title AND creator.
        decade: Optional decade filter (e.g. 1990 matches years 1990–1999).
        sort_by: Sort field — one of title, creator, year, rating.
        sort_dir: Sort direction — asc or desc.
        limit: Optional max results, used by agent tools as an alias for page_size.
        page: Page number (1-indexed).
        page_size: Number of items per page (max 200).
        db: DuckDB connection injected by FastAPI.

    Returns:
        PaginatedItems: Total count, pagination info, and item summaries.
    """
    conditions = ["1=1"]
    params: list = []

    if domain:
        conditions.append("t.domain = ?")
        params.append(domain)
    if status:
        conditions.append("t.status = ?")
        params.append(status)
    if min_rating is not None:
        conditions.append("r.rating >= ?")
        params.append(min_rating)
    if search:
        # Match against both title and creator so "Hot Water Music" finds all their albums
        conditions.append("(LOWER(t.title) LIKE ? OR LOWER(t.creator) LIKE ?)")
        pattern = f"%{search.lower()}%"
        params.extend([pattern, pattern])
    if decade is not None:
        if decade == 1900:
            # Special case: "Pre-1970" means any year before 1970
            conditions.append("t.year < 1970")
        else:
            # Normal decade: e.g. 1990 matches years 1990–1999
            conditions.append("t.year >= ? AND t.year < ?")
            params.extend([decade, decade + 10])

    # Genre filter — requires a JOIN with mart_item_categories
    category_join = ""
    if genre:
        category_join = "INNER JOIN mart_item_categories c ON t.id = c.item_id"
        conditions.append("c.genre = ?")
        params.append(genre)
        if sub_genre:
            conditions.append("c.sub_genre = ?")
            params.append(sub_genre)
    else:
        category_join = "LEFT JOIN mart_item_categories c ON t.id = c.item_id"

    where_clause = " AND ".join(conditions)

    # Resolve sort column (whitelist to prevent SQL injection)
    sort_col = _SORT_COLUMNS.get(sort_by, "t.title")
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"
    # NULLs last for all sort columns
    order_clause = f"{sort_col} {direction} NULLS LAST"

    # limit param is an alias for page_size, used by agent tools that pass ?limit=N directly
    effective_page_size = limit if limit is not None else page_size
    offset = (page - 1) * effective_page_size

    count_sql = f"""
        SELECT COUNT(*)
        FROM mart_unified_tastes t
        LEFT JOIN mart_ratings r ON t.id = r.item_id
        {category_join}
        WHERE {where_clause}
    """
    total = db.execute(count_sql, params).fetchone()[0]

    items_sql = f"""
        SELECT t.id, t.domain, t.title, t.creator, t.year, r.rating, t.status
        FROM mart_unified_tastes t
        LEFT JOIN mart_ratings r ON t.id = r.item_id
        {category_join}
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT ? OFFSET ?
    """
    rows = db.execute(items_sql, params + [effective_page_size, offset]).fetchall()

    return PaginatedItems(
        total=total,
        page=page,
        page_size=effective_page_size,
        items=[
            TasteItemSummary(
                id=row[0],
                domain=row[1],
                title=row[2],
                creator=row[3],
                year=row[4],
                rating=row[5],
                status=row[6],
            )
            for row in rows
        ],
    )


# ---------------------------------------------------------------------------
# GET /items/{item_id}
# ---------------------------------------------------------------------------


@router.get("/{item_id}", response_model=TasteItem)
def get_item(
    item_id: str,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> TasteItem:
    """Return a single taste item by its ID, with its current rating.

    Args:
        item_id: SHA256 item identifier.
        db: DuckDB connection injected by FastAPI.

    Returns:
        TasteItem: Full item representation.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    sql = """
        SELECT
            t.id, t.domain, t.source, t.source_id, t.title, t.creator,
            t.year, t.genres, t.cover_url, t.external_ids, t.status,
            t.date_added, t.date_consumed, NULL, NULL,
            r.rating
        FROM mart_unified_tastes t
        LEFT JOIN mart_ratings r ON t.id = r.item_id
        WHERE t.id = ?
    """
    row = db.execute(sql, [item_id]).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found.")
    return _row_to_item(row)


# ---------------------------------------------------------------------------
# POST /items
# ---------------------------------------------------------------------------


@router.post("/", response_model=TasteItem, status_code=201)
def create_item(
    payload: TasteItemCreate,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> TasteItem:
    """Create a new taste item in the gold layer.

    The item is inserted directly into mart_unified_tastes. If a rating
    is provided in the payload, it is also written to mart_ratings and
    a rating event is recorded in mart_rating_events.

    Args:
        payload: Item creation payload.
        db: DuckDB connection injected by FastAPI.

    Returns:
        TasteItem: The newly created item.

    Raises:
        HTTPException: 409 if an item with the same ID already exists.
    """
    item_id = _generate_item_id(
        payload.domain, payload.source, payload.source_id, payload.title
    )
    now = datetime.now(timezone.utc)

    # Check for duplicate
    existing = db.execute(
        "SELECT id FROM mart_unified_tastes WHERE id = ?", [item_id]
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail=f"Item '{item_id}' already exists.")

    # genres is stored as VARCHAR (comma-separated) in the gold table
    genres_str = ", ".join(payload.genres) if payload.genres else None

    db.execute(
        """
        INSERT INTO mart_unified_tastes (
            id, domain, source, source_id, title, creator, year,
            genres, cover_url, external_ids, status,
            date_added, date_consumed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            item_id,
            payload.domain,
            payload.source,
            payload.source_id,
            payload.title,
            payload.creator,
            payload.year,
            genres_str,
            payload.cover_url,
            json.dumps(payload.external_ids),
            payload.status,
            payload.date_added or now,
            payload.date_consumed,
        ],
    )

    # Write initial rating if provided
    if payload.rating is not None:
        rating_id = hashlib.sha256(f"{item_id}:user:{now.isoformat()}".encode()).hexdigest()
        db.execute(
            """
            INSERT INTO mart_ratings (id, item_id, rating, source, rated_at)
            VALUES (?, ?, ?, 'user', ?)
            """,
            [rating_id, item_id, payload.rating, now],
        )
        event_id = hashlib.sha256(f"{item_id}:event:{now.isoformat()}".encode()).hexdigest()
        db.execute(
            """
            INSERT INTO mart_rating_events (id, item_id, old_rating, new_rating, changed_by, changed_at)
            VALUES (?, ?, NULL, ?, 'user', ?)
            """,
            [event_id, item_id, payload.rating, now],
        )

    return get_item(item_id, db)


# ---------------------------------------------------------------------------
# DELETE /items/{item_id}
# ---------------------------------------------------------------------------


@router.delete("/{item_id}", status_code=204)
def delete_item(
    item_id: str,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> None:
    """Permanently delete a taste item and all its associated data.

    Removes the item from mart_unified_tastes, mart_ratings,
    mart_rating_events, and mart_item_categories.

    Note: this is a hard delete. Only items created manually (source='manual')
    can be meaningfully deleted — dbt-managed items will reappear on the next
    pipeline run. The API does not enforce this constraint; it is the caller's
    responsibility.

    Args:
        item_id: SHA256 item identifier.
        db: DuckDB connection injected by FastAPI.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    existing = db.execute(
        "SELECT id FROM mart_unified_tastes WHERE id = ?", [item_id]
    ).fetchone()
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found.")

    # Delete in dependency order (satellite tables first)
    db.execute("DELETE FROM mart_item_categories WHERE item_id = ?", [item_id])
    db.execute("DELETE FROM mart_rating_events WHERE item_id = ?", [item_id])
    db.execute("DELETE FROM mart_ratings WHERE item_id = ?", [item_id])
    db.execute("DELETE FROM mart_unified_tastes WHERE id = ?", [item_id])

    logger.info("Deleted item %s", item_id)


# ---------------------------------------------------------------------------
# PATCH /items/{item_id}
# ---------------------------------------------------------------------------


@router.patch("/{item_id}", response_model=TasteItem)
def update_item(
    item_id: str,
    payload: TasteItemUpdate,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> TasteItem:
    """Partially update a taste item.

    Only fields explicitly provided in the payload are updated.
    updated_at is always refreshed.

    Args:
        item_id: SHA256 item identifier.
        payload: Partial update payload.
        db: DuckDB connection injected by FastAPI.

    Returns:
        TasteItem: The updated item.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    existing = db.execute(
        "SELECT id FROM mart_unified_tastes WHERE id = ?", [item_id]
    ).fetchone()
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found.")

    updates: dict = {}
    if payload.title is not None:
        updates["title"] = payload.title
    if payload.creator is not None:
        updates["creator"] = payload.creator
    if payload.year is not None:
        updates["year"] = payload.year
    if payload.genres is not None:
        updates["genres"] = payload.genres
    if payload.cover_url is not None:
        updates["cover_url"] = payload.cover_url
    if payload.external_ids is not None:
        updates["external_ids"] = json.dumps(payload.external_ids)
    if payload.status is not None:
        updates["status"] = payload.status
    if payload.date_consumed is not None:
        updates["date_consumed"] = payload.date_consumed

    if updates:
        # updated_at does not exist in mart_unified_tastes (dbt-managed table)
        set_clause = ", ".join(f"{col} = ?" for col in updates)
        values = list(updates.values()) + [item_id]
        db.execute(
            f"UPDATE mart_unified_tastes SET {set_clause} WHERE id = ?", values
        )

    return get_item(item_id, db)