# api/schemas/category.py

"""Pydantic schemas for item category endpoints."""

from datetime import datetime

from pydantic import BaseModel, field_validator


class CategoryUpsert(BaseModel):
    """Payload for POST /items/{item_id}/category."""

    genre: str
    sub_genre: str | None = None

    @field_validator("genre")
    @classmethod
    def genre_not_empty(cls, v: str) -> str:
        """Ensure genre is not an empty string."""
        if not v.strip():
            raise ValueError("genre must not be empty")
        return v.strip()

    @field_validator("sub_genre")
    @classmethod
    def sub_genre_strip(cls, v: str | None) -> str | None:
        """Strip whitespace from sub_genre if provided."""
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class CategoryBatch(BaseModel):
    """Payload for POST /categories/batch."""

    item_ids: list[str]
    genre: str
    sub_genre: str | None = None

    @field_validator("item_ids")
    @classmethod
    def ids_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure at least one item_id is provided."""
        if not v:
            raise ValueError("item_ids must not be empty")
        if len(v) > 200:
            raise ValueError("Cannot batch more than 200 items at once")
        return v


class Category(BaseModel):
    """Current category for a taste item."""

    item_id: str
    domain: str
    genre: str
    sub_genre: str | None
    updated_at: datetime
