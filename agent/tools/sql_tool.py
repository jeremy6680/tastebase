# agent/tools/sql_tool.py

"""
SQL tool for the TasteBase LangGraph agent.

Converts a natural-language question into a DuckDB SQL query via an LLM,
executes it against the gold layer, and returns a formatted result.

Security: only SELECT queries are allowed. Any attempt to run a
write operation (INSERT, UPDATE, DELETE, DROP, etc.) is rejected.
"""

from __future__ import annotations

import logging
import os
import re

import duckdb
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gold layer schema — injected into the SQL generation prompt
# ---------------------------------------------------------------------------

GOLD_SCHEMA = """
Available tables (DuckDB gold layer):

mart_unified_tastes:
  id          VARCHAR  -- SHA256 primary key
  domain      VARCHAR  -- music | book | manga | movie | series | anime
  source      VARCHAR  -- musicbuddy | spotify | bookbuddy | goodreads | moviebuddy | letterboxd | trakt
  source_id   VARCHAR
  title       VARCHAR
  creator     VARCHAR  -- artist / author / director
  year        INTEGER
  genres      VARCHAR[]
  cover_url   VARCHAR
  external_ids JSON    -- {imdb, tmdb, isbn13, discogs_id, spotify_id, trakt_id}
  status      VARCHAR  -- owned | watched | read | wishlist | previously_owned | unread
  date_added  TIMESTAMP
  date_consumed TIMESTAMP
  created_at  TIMESTAMP
  updated_at  TIMESTAMP

mart_ratings:
  id          VARCHAR
  item_id     VARCHAR  -- FK → mart_unified_tastes.id
  rating      INTEGER  -- 1 to 5 (never NULL, never 0)
  source      VARCHAR  -- imported | user
  rated_at    TIMESTAMP
  notes       VARCHAR

mart_top_rated:
  domain      VARCHAR
  title       VARCHAR
  creator     VARCHAR
  year        INTEGER
  rating      INTEGER
  genres      VARCHAR[]

mart_taste_profile:
  domain      VARCHAR
  dimension   VARCHAR  -- genre | creator | decade
  value       VARCHAR
  item_count  INTEGER
  avg_rating  DOUBLE

mart_rating_events:
  id          VARCHAR
  item_id     VARCHAR
  old_rating  INTEGER
  new_rating  INTEGER
  changed_by  VARCHAR
  changed_at  TIMESTAMP

Useful join pattern:
  SELECT t.title, t.creator, t.domain, r.rating
  FROM mart_unified_tastes t
  LEFT JOIN mart_ratings r ON t.id = r.item_id

For genres (VARCHAR[]), use: list_contains(genres, 'rock') or array_to_string(genres, ', ')
Always add ORDER BY and LIMIT 20 unless the user asks for all results.
""".strip()

SQL_GENERATION_PROMPT = f"""
You are a DuckDB SQL expert. Generate a single SQL SELECT query to answer the user's question.

Rules:
- Output ONLY the SQL query, no explanation, no markdown fences.
- Only use SELECT. Never use INSERT, UPDATE, DELETE, DROP, CREATE, or any write operation.
- Only reference the tables listed in the schema below.
- For array columns (genres), use DuckDB array functions: list_contains(), array_to_string().
- Always add LIMIT 20 unless the user explicitly asks for all results.
- If the question cannot be answered with the available schema, output: CANNOT_ANSWER

Schema:
{GOLD_SCHEMA}
""".strip()

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_WRITE_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|REPLACE|MERGE)\b",
    re.IGNORECASE,
)


def _is_safe_query(sql: str) -> bool:
    """Return True if the query is a read-only SELECT statement.

    Args:
        sql: SQL string to validate.

    Returns:
        bool: True if safe (SELECT only), False otherwise.
    """
    stripped = sql.strip().upper()
    if not stripped.startswith("SELECT"):
        return False
    if _WRITE_PATTERN.search(sql):
        return False
    return True


def _format_results(rows: list[tuple], columns: list[str], limit: int = 20) -> str:
    """Format DuckDB result rows as a readable markdown table.

    Args:
        rows: List of result tuples from DuckDB.
        columns: Column names matching the SELECT.
        limit: Maximum number of rows to display.

    Returns:
        str: Markdown-formatted table, or a "no results" message.
    """
    if not rows:
        return "Aucun résultat trouvé pour cette requête."

    displayed = rows[:limit]

    # Header
    header = " | ".join(str(col) for col in columns)
    separator = " | ".join("---" for _ in columns)
    lines = [header, separator]

    for row in displayed:
        cells = []
        for cell in row:
            if isinstance(cell, list):
                cells.append(", ".join(str(v) for v in cell))
            elif cell is None:
                cells.append("—")
            else:
                cells.append(str(cell))
        lines.append(" | ".join(cells))

    result = "\n".join(lines)
    if len(rows) > limit:
        result += f"\n\n_({len(rows)} résultats au total, {limit} affichés)_"
    return result


def _get_llm() -> ChatAnthropic:
    """Instantiate the Anthropic LLM for SQL generation.

    Uses the ANTHROPIC_API_KEY environment variable.

    Returns:
        ChatAnthropic: Configured LLM instance.
    """
    return ChatAnthropic(
        model="claude-3-5-haiku-20241022",
        temperature=0,
        max_tokens=512,
    )


def _generate_sql(question: str) -> str:
    """Use the LLM to generate a SQL query from a natural-language question.

    Args:
        question: Natural-language question from the user.

    Returns:
        str: Generated SQL query, or "CANNOT_ANSWER" if the question
             cannot be answered from the available schema.
    """
    llm = _get_llm()
    messages = [
        SystemMessage(content=SQL_GENERATION_PROMPT),
        HumanMessage(content=question),
    ]
    response = llm.invoke(messages)
    sql = response.content.strip()

    # Strip accidental markdown fences
    if sql.startswith("```"):
        sql = re.sub(r"```(?:sql)?\n?", "", sql).replace("```", "").strip()

    return sql


def _execute_sql(sql: str, db_path: str) -> tuple[list[tuple], list[str]]:
    """Execute a validated SELECT query against the DuckDB warehouse.

    Args:
        sql: Safe SELECT query to execute.
        db_path: Absolute path to the DuckDB warehouse file.

    Returns:
        tuple: (rows, column_names)

    Raises:
        ValueError: If the query fails to execute.
    """
    try:
        conn = duckdb.connect(db_path, read_only=True)
        result = conn.execute(sql)
        rows = result.fetchall()
        columns = [desc[0] for desc in result.description]
        conn.close()
        return rows, columns
    except Exception as exc:
        raise ValueError(f"Erreur lors de l'exécution SQL : {exc}") from exc


# ---------------------------------------------------------------------------
# LangGraph tool
# ---------------------------------------------------------------------------


@tool
def sql_tool(question: str) -> str:
    """Query the TasteBase collection using natural language.

    Converts the question to a DuckDB SQL query, executes it against
    the gold layer (read-only), and returns a formatted result.

    Use this tool for any question about the collection: ratings, genres,
    top items, counts, comparisons across domains, etc.

    Args:
        question: Natural-language question about the collection.

    Returns:
        str: Formatted query result, or an error message if the query fails.
    """
    db_path = os.environ.get("DUCKDB_PATH", "data/warehouse.duckdb")

    logger.info("sql_tool called with question: %s", question)

    # Step 1 — Generate SQL
    try:
        sql = _generate_sql(question)
    except Exception as exc:
        logger.error("SQL generation failed: %s", exc)
        return f"Impossible de générer une requête SQL pour cette question : {exc}"

    logger.info("Generated SQL: %s", sql)

    # Step 2 — Handle unanswerable questions
    if sql == "CANNOT_ANSWER":
        return (
            "Je ne peux pas répondre à cette question avec les données disponibles. "
            "Les tables de la collection contiennent : films, séries, anime, livres, mangas, musique, "
            "avec leurs ratings, genres, créateurs et années."
        )

    # Step 3 — Safety check
    if not _is_safe_query(sql):
        logger.warning("Rejected unsafe SQL: %s", sql)
        return "Requête refusée : seules les requêtes SELECT sont autorisées."

    # Step 4 — Execute
    try:
        rows, columns = _execute_sql(sql, db_path)
    except ValueError as exc:
        logger.error("SQL execution failed: %s", exc)
        return str(exc)

    # Step 5 — Format and return
    return _format_results(rows, columns)