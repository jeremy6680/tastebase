# api/schemas/item.py

"""
Pydantic schemas for taste items.

TasteItem        — full item as returned by the API (read model)
TasteItemCreate  — payload for creating a new item (write model)
TasteItemUpdate  — payload for partial updates (all fields optional)
TasteItemSummary — lightweight version for list endpoints
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

VALID_DOMAINS = {"music", "book", "manga", "movie", "series", "anime"}
VALID_STATUSES = {
    "owned",
    "watched",
    "read",
    "wishlist",
    "previously_owned",
    "unread",
}


# ---------------------------------------------------------------------------
# Read model
# ---------------------------------------------------------------------------


class TasteItem(BaseModel):
    """Full representation of a unified taste item (gold layer)."""

    id: str = Field(..., description="SHA256(domain + source + source_id)")
    domain: str = Field(..., description="music | book | manga | movie | series | anime")
    source: str = Field(
        ...,
        description="musicbuddy | spotify | bookbuddy | goodreads | moviebuddy | letterboxd | trakt",
    )
    source_id: str | None = Field(None, description="Original ID in the source system")
    title: str
    creator: str | None = Field(None, description="Artist / author / director")
    year: int | None = None
    genres: list[str] = Field(default_factory=list)
    cover_url: str | None = None
    external_ids: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None
    date_added: datetime | None = None
    date_consumed: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Rating is joined from mart_ratings — may be None if unrated
    rating: int | None = Field(None, ge=1, le=5)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Write models
# ---------------------------------------------------------------------------


class TasteItemCreate(BaseModel):
    """Payload for creating a new taste item."""

    domain: str = Field(..., description="music | book | manga | movie | series | anime")
    source: str = Field(..., description="Source identifier")
    source_id: str | None = None
    title: str = Field(..., min_length=1)
    creator: str | None = None
    year: int | None = Field(None, ge=1800, le=2100)
    genres: list[str] = Field(default_factory=list)
    cover_url: str | None = None
    external_ids: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None
    date_added: datetime | None = None
    date_consumed: datetime | None = None
    rating: int | None = Field(None, ge=1, le=5)


class TasteItemUpdate(BaseModel):
    """Payload for partially updating a taste item (all fields optional)."""

    title: str | None = Field(None, min_length=1)
    creator: str | None = None
    year: int | None = Field(None, ge=1800, le=2100)
    genres: list[str] | None = None
    cover_url: str | None = None
    external_ids: dict[str, Any] | None = None
    status: str | None = None
    date_consumed: datetime | None = None


# ---------------------------------------------------------------------------
# Summary model (list endpoints)
# ---------------------------------------------------------------------------


class TasteItemSummary(BaseModel):
    """Lightweight item representation for paginated list responses."""

    id: str
    domain: str
    title: str
    creator: str | None = None
    year: int | None = None
    rating: int | None = Field(None, ge=1, le=5)
    status: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Paginated response wrapper
# ---------------------------------------------------------------------------


class PaginatedItems(BaseModel):
    """Wrapper for paginated list responses."""

    total: int
    page: int
    page_size: int
    items: list[TasteItemSummary]