"""Tests for TraktClient — all HTTP calls are mocked, no real API calls made."""

import pytest
from unittest.mock import MagicMock, patch
from ingestion.apis.trakt_client import TraktClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def trakt_env(monkeypatch):
    """Injects required Trakt environment variables for all tests."""
    monkeypatch.setenv("TRAKT_CLIENT_ID", "fake_client_id")
    monkeypatch.setenv("TRAKT_CLIENT_SECRET", "fake_client_secret")
    monkeypatch.setenv("TRAKT_ACCESS_TOKEN", "fake_access_token")
    monkeypatch.setenv("TRAKT_REFRESH_TOKEN", "fake_refresh_token")


@pytest.fixture
def client(trakt_env, tmp_path):
    """Returns a TraktClient instance with a temporary DuckDB path."""
    db_path = tmp_path / "test_warehouse.duckdb"
    return TraktClient(db_path=str(db_path))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(
    json_data: list | dict,
    status_code: int = 200,
    total_pages: int = 1,
) -> MagicMock:
    """Creates a mock httpx response for Trakt API calls.

    Args:
        json_data: Data to return from response.json().
        status_code: HTTP status code to simulate.
        total_pages: Value for the X-Pagination-Page-Count header.

    Returns:
        Configured MagicMock mimicking an httpx.Response.
    """
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    mock.headers = {"X-Pagination-Page-Count": str(total_pages)}
    return mock


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------


def test_init_success(trakt_env, tmp_path):
    """TraktClient initializes correctly when all env vars are present."""
    client = TraktClient(db_path=str(tmp_path / "test.duckdb"))
    assert client.source_name == "trakt"
    assert client.table_name == "raw_trakt"
    assert client.client_id == "fake_client_id"
    assert client.access_token == "fake_access_token"


def test_init_missing_env_var(tmp_path, monkeypatch):
    """TraktClient raises EnvironmentError when a required env var is missing."""
    monkeypatch.setenv("TRAKT_CLIENT_ID", "fake_client_id")
    monkeypatch.setenv("TRAKT_CLIENT_SECRET", "fake_client_secret")
    monkeypatch.setenv("TRAKT_ACCESS_TOKEN", "fake_access_token")
    # Force-remove the variable even if it exists in the real .env
    monkeypatch.delenv("TRAKT_REFRESH_TOKEN", raising=False)

    with pytest.raises(EnvironmentError, match="TRAKT_REFRESH_TOKEN"):
        TraktClient(db_path=str(tmp_path / "test.duckdb"))


# ---------------------------------------------------------------------------
# Token refresh tests
# ---------------------------------------------------------------------------


def test_refresh_access_token(client):
    """_refresh_access_token updates both access and refresh tokens."""
    mock_resp = _mock_response({
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
    })

    with patch("httpx.post", return_value=mock_resp):
        client._refresh_access_token()

    assert client.access_token == "new_access_token"
    assert client.refresh_token == "new_refresh_token"


# ---------------------------------------------------------------------------
# _get_paginated tests
# ---------------------------------------------------------------------------


def test_get_paginated_single_page(client):
    """_get_paginated returns all items from a single page."""
    mock_resp = _mock_response(
        [{"movie": {"title": "Inception"}}, {"movie": {"title": "Dune"}}],
        total_pages=1,
    )

    with patch("httpx.get", return_value=mock_resp):
        result = client._get_paginated("/users/me/watched/movies")

    assert len(result) == 2
    assert result[0]["movie"]["title"] == "Inception"


def test_get_paginated_multiple_pages(client):
    """_get_paginated fetches all pages and aggregates results."""
    page1 = _mock_response([{"movie": {"title": "Film A"}}], total_pages=2)
    page2 = _mock_response([{"movie": {"title": "Film B"}}], total_pages=2)

    with patch("httpx.get", side_effect=[page1, page2]):
        result = client._get_paginated("/users/me/watched/movies")

    assert len(result) == 2
    titles = [r["movie"]["title"] for r in result]
    assert "Film A" in titles
    assert "Film B" in titles


def test_get_paginated_retries_on_401(client):
    """_get_paginated refreshes the token and retries on a 401 response."""
    mock_401 = MagicMock()
    mock_401.status_code = 401
    mock_401.headers = {"X-Pagination-Page-Count": "1"}

    mock_200 = _mock_response([{"show": {"title": "Breaking Bad"}}], total_pages=1)

    with patch("httpx.get", side_effect=[mock_401, mock_200]), \
         patch.object(client, "_refresh_access_token") as mock_refresh:
        result = client._get_paginated("/users/me/watched/shows")

    mock_refresh.assert_called_once()
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Endpoint fetcher tests
# ---------------------------------------------------------------------------


def test_fetch_watched_movies(client):
    """_fetch_watched_movies returns all watched movies."""
    mock_resp = _mock_response(
        [{"movie": {"title": "The Matrix", "ids": {"imdb": "tt0133093"}}}],
        total_pages=1,
    )

    with patch("httpx.get", return_value=mock_resp):
        result = client._fetch_watched_movies()

    assert len(result) == 1
    assert result[0]["movie"]["title"] == "The Matrix"


def test_fetch_watched_shows(client):
    """_fetch_watched_shows returns all watched shows."""
    mock_resp = _mock_response(
        [{"show": {"title": "Dark", "ids": {"imdb": "tt5753856"}}}],
        total_pages=1,
    )

    with patch("httpx.get", return_value=mock_resp):
        result = client._fetch_watched_shows()

    assert len(result) == 1
    assert result[0]["show"]["title"] == "Dark"


def test_fetch_ratings_movies(client):
    """_fetch_ratings_movies returns all movie ratings."""
    mock_resp = _mock_response(
        [{"rating": 8, "movie": {"title": "Parasite", "ids": {"imdb": "tt6751668"}}}],
        total_pages=1,
    )

    with patch("httpx.get", return_value=mock_resp):
        result = client._fetch_ratings_movies()

    assert len(result) == 1
    # Rating must be stored as-is in bronze (no conversion to 1-5 here)
    assert result[0]["rating"] == 8


def test_fetch_ratings_shows(client):
    """_fetch_ratings_shows returns all show ratings."""
    mock_resp = _mock_response(
        [{"rating": 10, "show": {"title": "Chernobyl", "ids": {"imdb": "tt7366338"}}}],
        total_pages=1,
    )

    with patch("httpx.get", return_value=mock_resp):
        result = client._fetch_ratings_shows()

    assert len(result) == 1
    assert result[0]["rating"] == 10


# ---------------------------------------------------------------------------
# _parse tests
# ---------------------------------------------------------------------------


def test_parse_returns_records_for_all_endpoints(client):
    """_parse returns records tagged with all four endpoint names."""
    mock_resp = _mock_response(
        [{"movie": {"title": "Test"}}],
        total_pages=1,
    )

    with patch("httpx.get", return_value=mock_resp):
        records = client._parse()

    endpoints = {r["endpoint"] for r in records}
    assert endpoints == {"watched_movies", "watched_shows", "ratings_movies", "ratings_shows"}


def test_parse_each_record_has_required_keys(client):
    """_parse records all contain endpoint, fetched_at, and payload keys."""
    mock_resp = _mock_response([{"movie": {"title": "Test"}}], total_pages=1)

    with patch("httpx.get", return_value=mock_resp):
        records = client._parse()

    for record in records:
        assert "endpoint" in record
        assert "fetched_at" in record
        assert "payload" in record


def test_parse_continues_on_endpoint_failure(client):
    """_parse skips a failed endpoint and continues with the rest."""
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First endpoint (watched_movies) fails
            raise Exception("Simulated network error")
        return _mock_response([{"show": {"title": "Test"}}], total_pages=1)

    with patch("httpx.get", side_effect=side_effect):
        records = client._parse()

    endpoints = {r["endpoint"] for r in records}
    assert "watched_movies" not in endpoints
    assert len(records) > 0


def test_parse_ratings_stored_raw(client):
    """_parse stores Trakt ratings as-is — no conversion to 1-5 scale in bronze."""
    mock_resp = _mock_response(
        [{"rating": 9, "movie": {"title": "Test"}}],
        total_pages=1,
    )

    with patch("httpx.get", return_value=mock_resp):
        records = client._parse()

    # Find a ratings record and verify the raw rating is preserved in payload
    ratings_records = [r for r in records if "ratings" in r["endpoint"]]
    assert len(ratings_records) > 0
    # The payload string must contain the original rating value
    assert "9" in ratings_records[0]["payload"]


# ---------------------------------------------------------------------------
# _write_to_bronze tests
# ---------------------------------------------------------------------------


def test_write_to_bronze_creates_table(client):
    """_write_to_bronze creates raw_trakt table and inserts all records."""
    import duckdb
    from datetime import datetime, timezone

    records = [
        {
            "endpoint": "watched_movies",
            "fetched_at": "2026-01-01T00:00:00+00:00",
            "payload": "{'movie': {'title': 'Test'}}",
            "_source": "trakt",
            "_loaded_at": datetime.now(timezone.utc),
        }
    ]

    client._write_to_bronze(records)

    con = duckdb.connect(str(client.db_path))
    count = con.execute("SELECT COUNT(*) FROM raw_trakt").fetchone()[0]
    con.close()

    assert count == 1


def test_write_to_bronze_skips_on_empty(client, caplog):
    """_write_to_bronze logs a warning and skips writing when records is empty."""
    import logging

    with caplog.at_level(logging.WARNING):
        client._write_to_bronze([])

    assert "skipping" in caplog.text.lower()


def test_write_to_bronze_full_refresh(client):
    """_write_to_bronze replaces existing data on each run (full refresh)."""
    import duckdb
    from datetime import datetime, timezone

    def make_record(title: str) -> dict:
        return {
            "endpoint": "watched_movies",
            "fetched_at": "2026-01-01T00:00:00+00:00",
            "payload": f"{{'movie': '{title}'}}",
            "_source": "trakt",
            "_loaded_at": datetime.now(timezone.utc),
        }

    # First write — 2 records
    client._write_to_bronze([make_record("Film A"), make_record("Film B")])

    # Second write — 1 record (should replace, not append)
    client._write_to_bronze([make_record("Film C")])

    con = duckdb.connect(str(client.db_path))
    count = con.execute("SELECT COUNT(*) FROM raw_trakt").fetchone()[0]
    con.close()

    assert count == 1