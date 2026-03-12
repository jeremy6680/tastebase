# api/schemas/rating.py

"""
Pydantic schemas for ratings and rating events.

Rating       — current rating for an item (read model)
RatingCreate — payload for adding or updating a rating
RatingEvent  — single entry from the append-only audit trail
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Rating(BaseModel):
    """Current rating for a taste item."""

    id: str
    item_id: str
    rating: int = Field(..., ge=1, le=5)
    source: str = Field(..., description="imported | user")
    rated_at: datetime
    notes: str | None = None

    model_config = {"from_attributes": True}


class RatingCreate(BaseModel):
    """Payload for creating or updating a rating on an item."""

    rating: int = Field(..., ge=1, le=5)
    notes: str | None = None


class RatingEvent(BaseModel):
    """Single entry from the append-only rating audit trail."""

    id: str
    item_id: str
    old_rating: int | None = Field(None, ge=1, le=5)
    new_rating: int = Field(..., ge=1, le=5)
    changed_by: str = Field(default="user")
    changed_at: datetime

    model_config = {"from_attributes": True}