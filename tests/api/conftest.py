# tests/api/conftest.py

"""
pytest fixtures for API tests.

Provides:
- in_memory_db: a DuckDB in-memory connection pre-populated with the gold schema
- client: a TestClient with get_db overridden to use in_memory_db
"""

import hashlib
from datetime import datetime, timezone

import duckdb
import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_db
from api.main import app


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

GOLD_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS mart_unified_tastes (
    id           VARCHAR PRIMARY KEY,
    domain       VARCHAR NOT NULL,
    source       VARCHAR NOT NULL,
    source_id    VARCHAR,
    title        VARCHAR NOT NULL,
    creator      VARCHAR,
    year         INTEGER,
    genres       VARCHAR[],
    cover_url    VARCHAR,
    external_ids JSON,
    status       VARCHAR,
    date_added   TIMESTAMPTZ,
    date_consumed TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mart_ratings (
    id       VARCHAR PRIMARY KEY,
    item_id  VARCHAR REFERENCES mart_unified_tastes(id),
    rating   INTEGER CHECK (rating BETWEEN 1 AND 5),
    source   VARCHAR,
    rated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    notes    VARCHAR
);

CREATE TABLE IF NOT EXISTS mart_rating_events (
    id          VARCHAR PRIMARY KEY,
    item_id     VARCHAR,
    old_rating  INTEGER,
    new_rating  INTEGER,
    changed_by  VARCHAR DEFAULT 'user',
    changed_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mart_taste_profile (
    domain      VARCHAR,
    genre       VARCHAR,
    item_count  INTEGER
);
"""


def _make_item_id(domain: str, source: str, title: str) -> str:
    """Generate a test item ID using the same logic as the API."""
    return hashlib.sha256(f"{domain}:{source}:{title}".encode()).hexdigest()


@pytest.fixture()
def in_memory_db() -> duckdb.DuckDBPyConnection:
    """Provide a fresh in-memory DuckDB with the gold schema and seed data.

    Yields:
        duckdb.DuckDBPyConnection: Ready-to-use connection.
    """
    conn = duckdb.connect(":memory:")
    conn.execute(GOLD_SCHEMA_SQL)

    # Seed: one item per domain
    now = datetime.now(timezone.utc)
    seeds = [
        ("music", "musicbuddy", "Kind of Blue", "Miles Davis", 1959, 5),
        ("book", "bookbuddy", "Dune", "Frank Herbert", 1965, 4),
        ("manga", "bookbuddy", "Berserk", "Kentaro Miura", 1989, 5),
        ("movie", "letterboxd", "2001: A Space Odyssey", "Stanley Kubrick", 1968, 5),
        ("series", "trakt", "The Wire", "David Simon", 2002, 5),
        ("anime", "trakt", "Fullmetal Alchemist: Brotherhood", "Yasuhiro Irie", 2009, 5),
    ]

    for domain, source, title, creator, year, rating in seeds:
        item_id = _make_item_id(domain, source, title)
        conn.execute(
            """
            INSERT INTO mart_unified_tastes
            (id, domain, source, title, creator, year, genres, external_ids, date_added, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, [], '{}', ?, ?, ?)
            """,
            [item_id, domain, source, title, creator, year, now, now, now],
        )
        rating_id = _make_item_id(domain, source, f"{title}:rating")
        conn.execute(
            "INSERT INTO mart_ratings (id, item_id, rating, source, rated_at) VALUES (?, ?, ?, 'imported', ?)",
            [rating_id, item_id, rating, now],
        )

    yield conn
    conn.close()


@pytest.fixture()
def client(in_memory_db: duckdb.DuckDBPyConnection) -> TestClient:
    """Provide a FastAPI TestClient with DuckDB dependency overridden.

    The get_db dependency is replaced by a generator that yields the
    in-memory connection without closing it between requests (the fixture
    manages the lifecycle).

    Args:
        in_memory_db: In-memory DuckDB fixture.

    Returns:
        TestClient: Configured test client.
    """

    def override_get_db():
        yield in_memory_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()