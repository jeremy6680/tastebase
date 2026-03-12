# api/routers/ratings.py

"""
Rating endpoints.

POST /items/{item_id}/ratings  — add or update a rating for an item
GET  /items/{item_id}/ratings  — get current rating for an item
GET  /items/{item_id}/ratings/history  — full rating event log for an item
"""

import hashlib
import logging
from datetime import datetime, timezone

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_db
from api.schemas.rating import Rating, RatingCreate, RatingEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/items", tags=["ratings"])


# ---------------------------------------------------------------------------
# GET /items/{item_id}/ratings
# ---------------------------------------------------------------------------


@router.get("/{item_id}/ratings", response_model=Rating | None)
def get_rating(
    item_id: str,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> Rating | None:
    """Return the current rating for an item, or null if unrated.

    Args:
        item_id: SHA256 item identifier.
        db: DuckDB connection injected by FastAPI.

    Returns:
        Rating | None: Current rating, or None if the item is unrated.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    _assert_item_exists(item_id, db)

    row = db.execute(
        "SELECT id, item_id, rating, source, rated_at, notes FROM mart_ratings WHERE item_id = ?",
        [item_id],
    ).fetchone()

    if row is None:
        return None

    return Rating(
        id=row[0],
        item_id=row[1],
        rating=row[2],
        source=row[3],
        rated_at=row[4],
        notes=row[5],
    )


# ---------------------------------------------------------------------------
# POST /items/{item_id}/ratings
# ---------------------------------------------------------------------------


@router.post("/{item_id}/ratings", response_model=Rating, status_code=201)
def upsert_rating(
    item_id: str,
    payload: RatingCreate,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> Rating:
    """Add or update the rating for a taste item.

    - If no rating exists: INSERT into mart_ratings, record event with old_rating=NULL.
    - If a rating exists: UPDATE mart_ratings, record event with old_rating=previous value.

    The rating event log (mart_rating_events) is always appended — never modified.

    Args:
        item_id: SHA256 item identifier.
        payload: Rating value (1–5) and optional notes.
        db: DuckDB connection injected by FastAPI.

    Returns:
        Rating: The current (new) rating.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    _assert_item_exists(item_id, db)

    now = datetime.now(timezone.utc)

    # Check for existing rating
    existing_row = db.execute(
        "SELECT id, rating FROM mart_ratings WHERE item_id = ?", [item_id]
    ).fetchone()

    old_rating: int | None = None

    if existing_row:
        # UPDATE existing rating
        old_rating = existing_row[1]
        db.execute(
            "UPDATE mart_ratings SET rating = ?, source = 'user', rated_at = ?, notes = ? WHERE item_id = ?",
            [payload.rating, now, payload.notes, item_id],
        )
        rating_id = existing_row[0]
    else:
        # INSERT new rating
        rating_id = hashlib.sha256(f"{item_id}:user:{now.isoformat()}".encode()).hexdigest()
        db.execute(
            """
            INSERT INTO mart_ratings (id, item_id, rating, source, rated_at, notes)
            VALUES (?, ?, ?, 'user', ?, ?)
            """,
            [rating_id, item_id, payload.rating, now, payload.notes],
        )

    # Always append a rating event (audit trail — never modify this table)
    event_id = hashlib.sha256(f"{item_id}:event:{now.isoformat()}".encode()).hexdigest()
    db.execute(
        """
        INSERT INTO mart_rating_events (id, item_id, old_rating, new_rating, changed_by, changed_at)
        VALUES (?, ?, ?, ?, 'user', ?)
        """,
        [event_id, item_id, old_rating, payload.rating, now],
    )

    return Rating(
        id=rating_id,
        item_id=item_id,
        rating=payload.rating,
        source="user",
        rated_at=now,
        notes=payload.notes,
    )


# ---------------------------------------------------------------------------
# GET /items/{item_id}/ratings/history
# ---------------------------------------------------------------------------


@router.get("/{item_id}/ratings/history", response_model=list[RatingEvent])
def get_rating_history(
    item_id: str,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
) -> list[RatingEvent]:
    """Return the full rating event history for an item (oldest first).

    Args:
        item_id: SHA256 item identifier.
        db: DuckDB connection injected by FastAPI.

    Returns:
        list[RatingEvent]: All rating events, ordered by changed_at ASC.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    _assert_item_exists(item_id, db)

    rows = db.execute(
        """
        SELECT id, item_id, old_rating, new_rating, changed_by, changed_at
        FROM mart_rating_events
        WHERE item_id = ?
        ORDER BY changed_at ASC
        """,
        [item_id],
    ).fetchall()

    return [
        RatingEvent(
            id=row[0],
            item_id=row[1],
            old_rating=row[2],
            new_rating=row[3],
            changed_by=row[4],
            changed_at=row[5],
        )
        for row in rows
    ]


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