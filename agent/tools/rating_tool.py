# agent/tools/rating_tool.py

"""
Rating tool for the TasteBase LangGraph agent.

Provides two operations:
- search_item_for_rating: find an item by title to confirm before rating
- submit_rating: send a rating to the FastAPI backend (POST /ratings)

Design rule (DEC-011): the agent never touches DuckDB directly.
All writes go through the FastAPI backend.

Usage flow (enforced by the agent graph):
  1. Agent calls search_item_for_rating(title) → shows candidates to user
  2. User confirms the correct item and the desired rating
  3. Agent calls submit_rating(item_id, rating) → rating is persisted
"""

from __future__ import annotations

import logging
import os

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def _get_api_url(path: str) -> str:
    """Build a full API URL from a relative path.

    Args:
        path: Relative path, e.g. "/items" or "/ratings".

    Returns:
        str: Full URL against the FastAPI backend.
    """
    return f"{_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _search_items(title: str, limit: int = 5) -> list[dict]:
    """Query the FastAPI backend for items matching a title.

    Uses the GET /items endpoint with a title filter.
    Returns at most `limit` results.

    Args:
        title: Partial or full title to search for.
        limit: Maximum number of results to return.

    Returns:
        list[dict]: List of item dicts with at least id, title, creator, domain, year.

    Raises:
        RuntimeError: If the API call fails.
    """
    url = _get_api_url("/items")
    try:
        response = httpx.get(url, params={"title": title, "limit": limit}, timeout=10)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"API error {exc.response.status_code} while searching for '{title}': "
            f"{exc.response.text}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Could not reach the TasteBase API at {_API_BASE_URL}: {exc}"
        ) from exc


def _post_rating(item_id: str, rating: int, notes: str | None = None) -> dict:
    """Send a rating upsert to the FastAPI backend.

    Calls POST /ratings with item_id, rating, and optional notes.
    The backend handles the insert-or-update logic and appends to
    mart_rating_events (DEC-012).

    Args:
        item_id: The SHA256 ID of the item in mart_unified_tastes.
        rating: Integer rating between 1 and 5.
        notes: Optional free-text note attached to the rating.

    Returns:
        dict: The created/updated rating object from the API.

    Raises:
        RuntimeError: If the API call fails or returns an error.
    """
    url = _get_api_url("/ratings")
    payload: dict = {"item_id": item_id, "rating": rating, "source": "user"}
    if notes:
        payload["notes"] = notes

    try:
        response = httpx.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"API error {exc.response.status_code} while submitting rating: "
            f"{exc.response.text}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Could not reach the TasteBase API at {_API_BASE_URL}: {exc}"
        ) from exc


def _format_candidates(items: list[dict]) -> str:
    """Format a list of candidate items as a readable string for the agent.

    Args:
        items: List of item dicts from the API.

    Returns:
        str: Human-readable list of candidates with index, domain, title, creator, year.
    """
    if not items:
        return "Aucun item trouvé avec ce titre."

    lines = ["Voici les items correspondants :\n"]
    for i, item in enumerate(items, start=1):
        creator = item.get("creator") or "—"
        year = item.get("year") or "—"
        domain = item.get("domain", "—")
        title = item.get("title", "—")
        item_id = item.get("id", "—")
        lines.append(
            f"{i}. [{domain}] **{title}** — {creator} ({year})\n"
            f"   ID : `{item_id}`"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LangGraph tools
# ---------------------------------------------------------------------------


@tool
def search_item_for_rating(title: str) -> str:
    """Search the collection for items matching a title, in preparation for rating.

    Always call this tool BEFORE submit_rating to find the correct item ID
    and display candidates to the user for confirmation.

    Do NOT call submit_rating until the user has explicitly confirmed:
    - which item they want to rate (by ID)
    - what rating they want to assign (1–5)

    Args:
        title: Partial or full title of the item to rate.
            Example: "Dune", "Blade Runner", "1984"

    Returns:
        str: Formatted list of matching items with their IDs, domains, and metadata.
             Returns an error message if the search fails or no items are found.
    """
    logger.info("search_item_for_rating called with title: %s", title)

    try:
        items = _search_items(title)
    except RuntimeError as exc:
        logger.error("Item search failed: %s", exc)
        return f"Erreur lors de la recherche : {exc}"

    return _format_candidates(items)


@tool
def submit_rating(item_id: str, rating: int, notes: str = "") -> str:
    """Submit a rating for a specific item via the TasteBase FastAPI backend.

    Only call this tool AFTER the user has confirmed the item ID and rating
    via search_item_for_rating. Never guess an item_id.

    The rating is persisted in mart_ratings and an event is appended to
    mart_rating_events (append-only audit trail, DEC-012).

    Args:
        item_id: The exact SHA256 ID of the item (from search_item_for_rating).
        rating: Integer rating between 1 and 5 inclusive.
        notes: Optional note to attach to this rating (default: empty string).

    Returns:
        str: Confirmation message with the recorded rating, or an error message.
    """
    logger.info("submit_rating called — item_id: %s, rating: %d", item_id, rating)

    # Validate rating range before hitting the API
    if not (1 <= rating <= 5):
        return (
            f"Rating invalide : {rating}. "
            "Les notes doivent être un entier entre 1 et 5."
        )

    try:
        result = _post_rating(item_id, rating, notes or None)
    except RuntimeError as exc:
        logger.error("submit_rating failed: %s", exc)
        return f"Erreur lors de l'enregistrement du rating : {exc}"

    recorded_rating = result.get("rating", rating)
    return (
        f"✅ Rating enregistré : **{recorded_rating}/5** pour l'item `{item_id}`."
    )