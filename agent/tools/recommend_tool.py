# agent/tools/recommend_tool.py

"""
Recommendation tool for the TasteBase LangGraph agent.

Generates cross-domain cultural recommendations based on the user's
taste profile (top-rated items, preferred genres, top creators, decades).

Strategy (v1): prompt-based recommendation via LLM.
The tool fetches the taste profile and top-rated items from the FastAPI
backend, then asks the LLM to suggest items the user has NOT yet consumed,
cross-referencing across domains (e.g. manga fan → movie suggestions).

No embeddings or ML are used in v1 — see backlog in NEXT_STEPS.md.
"""

from __future__ import annotations

import logging
import os

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_api_url(path: str) -> str:
    """Build a full API URL from a relative path.

    Args:
        path: Relative path, e.g. "/stats/taste-profile".

    Returns:
        str: Full URL against the FastAPI backend.
    """
    return f"{_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _fetch_taste_profile() -> list[dict]:
    """Fetch the full taste profile from GET /stats/taste-profile.

    Returns:
        list[dict]: Rows from mart_taste_profile (stat_type, dimension, value_int, etc.)

    Raises:
        RuntimeError: If the API call fails.
    """
    url = _get_api_url("/stats/taste-profile")
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("profile", [])
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"API error {exc.response.status_code} fetching taste profile: "
            f"{exc.response.text}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Could not reach the TasteBase API at {_API_BASE_URL}: {exc}"
        ) from exc


def _fetch_top_rated(domain: str | None = None, limit: int = 20) -> list[dict]:
    """Fetch top-rated items from GET /stats/top-rated.

    Args:
        domain: Optional domain filter (music, book, manga, movie, series, anime).
        limit: Maximum number of items to retrieve.

    Returns:
        list[dict]: Top-rated item summaries (title, creator, domain, year, rating).

    Raises:
        RuntimeError: If the API call fails.
    """
    url = _get_api_url("/stats/top-rated")
    params: dict = {"limit": limit}
    if domain:
        params["domain"] = domain

    try:
        response = httpx.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"API error {exc.response.status_code} fetching top-rated: "
            f"{exc.response.text}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Could not reach the TasteBase API at {_API_BASE_URL}: {exc}"
        ) from exc


def _build_taste_context(
    profile: list[dict],
    top_rated: list[dict],
) -> str:
    """Format taste profile and top-rated items into a readable context string for the LLM.

    Args:
        profile: Rows from mart_taste_profile.
        top_rated: Top-rated item summaries.

    Returns:
        str: Formatted context string to inject into the recommendation prompt.
    """
    lines: list[str] = []

    # --- Domain stats ---
    domain_rows = [r for r in profile if r.get("stat_type") == "domain_stats"]
    if domain_rows:
        lines.append("## Collection overview")
        for row in domain_rows:
            domain = row.get("dimension", "?")
            details = row.get("details") or {}
            total = details.get("total_items", 0)
            avg = details.get("avg_rating", "—")
            lines.append(f"- {domain}: {total} items, avg rating {avg}/5")

    # --- Top genres ---
    genre_rows = sorted(
        [r for r in profile if r.get("stat_type") == "top_genre"],
        key=lambda r: r.get("value_int", 0),
        reverse=True,
    )[:15]
    if genre_rows:
        lines.append("\n## Top genres")
        genres_str = ", ".join(r.get("dimension", "") for r in genre_rows)
        lines.append(genres_str)

    # --- Top creators ---
    creator_rows = sorted(
        [r for r in profile if r.get("stat_type") == "top_creator"],
        key=lambda r: r.get("value_int", 0),
        reverse=True,
    )[:10]
    if creator_rows:
        lines.append("\n## Favourite creators")
        for row in creator_rows:
            creator = row.get("dimension", "?")
            domain = row.get("sub_dimension", "?")
            count = row.get("value_int", 0)
            avg = row.get("value_float", "—")
            lines.append(f"- {creator} ({domain}): {count} items, avg {avg}/5")

    # --- Favourite decades ---
    decade_rows = sorted(
        [r for r in profile if r.get("stat_type") == "decade"],
        key=lambda r: r.get("value_int", 0),
        reverse=True,
    )[:5]
    if decade_rows:
        lines.append("\n## Favourite decades")
        decades_str = ", ".join(r.get("dimension", "") for r in decade_rows)
        lines.append(decades_str)

    # --- Top-rated items (sample) ---
    if top_rated:
        lines.append("\n## Highest-rated items (sample)")
        for item in top_rated[:15]:
            title = item.get("title", "?")
            domain = item.get("domain", "?")
            creator = item.get("creator") or "—"
            year = item.get("year") or "—"
            rating = item.get("rating", "?")
            lines.append(f"- [{domain}] {title} — {creator} ({year}) ★{rating}")

    return "\n".join(lines)


def _get_llm() -> ChatAnthropic:
    """Instantiate the Anthropic LLM for recommendation generation.

    Returns:
        ChatAnthropic: Configured LLM instance (Haiku for speed).
    """
    return ChatAnthropic(
        model="claude-3-5-haiku-20241022",
        temperature=0.7,   # slightly creative for recommendations
        max_tokens=1024,
    )


def _generate_recommendations(request: str, taste_context: str) -> str:
    """Ask the LLM to generate recommendations based on the user's taste context.

    Args:
        request: The user's recommendation request in natural language.
        taste_context: Formatted taste profile context string.

    Returns:
        str: LLM-generated recommendation text.
    """
    system_prompt = """
You are a cultural recommendation assistant with deep knowledge of movies, series, anime,
books, manga, and music.

You have been given the user's personal taste profile extracted from their collection database.
Your job is to recommend items they have NOT yet consumed, based on their tastes.

Rules:
- Recommend 5 to 8 items maximum.
- Be specific: give title, creator, year, domain, and a one-sentence explanation of why.
- Cross-domain recommendations are encouraged when relevant
  (e.g. "if you love cyberpunk manga, try these movies").
- Never recommend items that are obviously already in their collection
  (you can see their top-rated items as a hint).
- Format each recommendation clearly: "**Title** (domain, year) — Creator. Why: ..."
- Respond in the same language as the user's request.
""".strip()

    user_message = f"""
## User's taste profile

{taste_context}

---

## User's request

{request}
""".strip()

    llm = _get_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]
    response = llm.invoke(messages)
    return response.content.strip()


# ---------------------------------------------------------------------------
# LangGraph tool
# ---------------------------------------------------------------------------


@tool
def recommend_tool(request: str) -> str:
    """Generate cross-domain cultural recommendations based on the user's taste profile.

    Fetches the user's taste profile (genres, creators, decades, top-rated items)
    from the FastAPI backend, then uses an LLM to suggest items the user has not
    yet consumed, tailored to their tastes and the specific request.

    Use this tool when the user asks for recommendations, suggestions, or
    "what should I watch/read/listen to next" questions.

    Examples of requests this tool handles:
    - "Recommande-moi des films similaires à Blade Runner"
    - "Qu'est-ce que je devrais lire si j'aime la SF ?"
    - "Give me anime recommendations based on my tastes"
    - "What manga would you suggest for a fan of Denis Villeneuve films?"

    Args:
        request: The user's recommendation request in natural language.

    Returns:
        str: A list of 5–8 tailored recommendations with titles, creators,
             years, domains, and explanations. Returns an error message if
             the profile or top-rated data cannot be fetched.
    """
    logger.info("recommend_tool called with request: %s", request)

    # Step 1 — Fetch taste data from the API
    try:
        profile = _fetch_taste_profile()
    except RuntimeError as exc:
        logger.error("Failed to fetch taste profile: %s", exc)
        return f"Impossible de récupérer le profil de goûts : {exc}"

    try:
        top_rated = _fetch_top_rated(limit=20)
    except RuntimeError as exc:
        logger.error("Failed to fetch top-rated items: %s", exc)
        return f"Impossible de récupérer les items les mieux notés : {exc}"

    # Step 2 — Build context string
    taste_context = _build_taste_context(profile, top_rated)

    if not taste_context.strip():
        return (
            "Le profil de goûts est vide. "
            "Commence par ajouter des items à ta collection et note-en quelques-uns !"
        )

    # Step 3 — Generate recommendations via LLM
    try:
        recommendations = _generate_recommendations(request, taste_context)
    except Exception as exc:
        logger.error("Recommendation generation failed: %s", exc)
        return f"Erreur lors de la génération des recommandations : {exc}"

    return recommendations