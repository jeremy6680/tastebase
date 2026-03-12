"""Tests for SpotifyClient — all HTTP calls are mocked, no real API calls made."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from ingestion.apis.spotify_client import SpotifyClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def spotify_env(monkeypatch):
    """Injects required Spotify environment variables for all tests."""
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "fake_client_id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "fake_client_secret")
    monkeypatch.setenv("SPOTIFY_ACCESS_TOKEN", "fake_access_token")
    monkeypatch.setenv("SPOTIFY_REFRESH_TOKEN", "fake_refresh_token")


@pytest.fixture
def client(spotify_env, tmp_path):
    """Returns a SpotifyClient instance with a temporary DuckDB path."""
    db_path = tmp_path / "test_warehouse.duckdb"
    return SpotifyClient(db_path=str(db_path))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Creates a mock httpx response with the given JSON body and status code.

    Args:
        json_data: Data to return from response.json().
        status_code: HTTP status code to simulate.

    Returns:
        Configured MagicMock mimicking an httpx.Response.
    """
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    mock.headers = {}
    return mock


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------


def test_init_success(spotify_env, tmp_path):
    """SpotifyClient initializes correctly when all env vars are present."""
    client = SpotifyClient(db_path=str(tmp_path / "test.duckdb"))
    assert client.source_name == "spotify"
    assert client.table_name == "raw_spotify"
    assert client.client_id == "fake_client_id"
    assert client.access_token == "fake_access_token"


def test_init_missing_env_var(tmp_path, monkeypatch):
    """SpotifyClient raises EnvironmentError when a required env var is missing."""
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "fake_client_id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "fake_client_secret")
    monkeypatch.setenv("SPOTIFY_ACCESS_TOKEN", "fake_access_token")
    # Force-remove the variable even if it exists in the real .env
    monkeypatch.delenv("SPOTIFY_REFRESH_TOKEN", raising=False)

    with pytest.raises(EnvironmentError, match="SPOTIFY_REFRESH_TOKEN"):
        SpotifyClient(db_path=str(tmp_path / "test.duckdb"))


# ---------------------------------------------------------------------------
# Token refresh tests
# ---------------------------------------------------------------------------


def test_refresh_access_token(client):
    """_refresh_access_token updates self.access_token from the API response."""
    mock_resp = _mock_response({"access_token": "new_token_abc"})

    with patch("httpx.post", return_value=mock_resp):
        client._refresh_access_token()

    assert client.access_token == "new_token_abc"


# ---------------------------------------------------------------------------
# _get tests
# ---------------------------------------------------------------------------


def test_get_success(client):
    """_get returns parsed JSON on a successful 200 response."""
    mock_resp = _mock_response({"items": [{"id": "album1"}]})

    with patch("httpx.get", return_value=mock_resp):
        result = client._get("https://api.spotify.com/v1/me/albums")

    assert result == {"items": [{"id": "album1"}]}


def test_get_retries_on_401(client):
    """_get refreshes the token and retries once on a 401 response."""
    mock_401 = MagicMock()
    mock_401.status_code = 401
    mock_401.headers = {}

    mock_200 = _mock_response({"items": []})

    with patch("httpx.get", side_effect=[mock_401, mock_200]) as mock_get, \
         patch.object(client, "_refresh_access_token") as mock_refresh:
        result = client._get("https://api.spotify.com/v1/me/albums")

    mock_refresh.assert_called_once()
    assert result == {"items": []}


def test_get_retries_on_429(client):
    """_get waits Retry-After seconds and retries on a 429 response."""
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.headers = {"Retry-After": "1"}

    mock_200 = _mock_response({"items": [{"id": "track1"}]})

    with patch("httpx.get", side_effect=[mock_429, mock_200]), \
         patch("time.sleep") as mock_sleep:
        result = client._get("https://api.spotify.com/v1/me/top/tracks")

    mock_sleep.assert_called_once_with(1)
    assert result == {"items": [{"id": "track1"}]}


# ---------------------------------------------------------------------------
# Endpoint fetcher tests
# ---------------------------------------------------------------------------


def test_fetch_saved_albums_single_page(client):
    """_fetch_saved_albums returns all items from a single page response."""
    mock_resp = _mock_response({
        "items": [{"album": {"id": "a1"}}, {"album": {"id": "a2"}}],
        "next": None,
    })

    with patch.object(client, "_get", return_value=mock_resp.json()):
        result = client._fetch_saved_albums()

    assert len(result) == 2
    assert result[0]["album"]["id"] == "a1"


def test_fetch_saved_albums_paginates(client):
    """_fetch_saved_albums follows the `next` cursor across multiple pages."""
    page1 = {"items": [{"album": {"id": "a1"}}], "next": "https://api.spotify.com/v1/me/albums?offset=1"}
    page2 = {"items": [{"album": {"id": "a2"}}], "next": None}

    with patch.object(client, "_get", side_effect=[page1, page2]):
        result = client._fetch_saved_albums()

    assert len(result) == 2


def test_fetch_recently_played(client):
    """_fetch_recently_played returns up to 50 tracks."""
    mock_data = {"items": [{"track": {"id": f"t{i}"}} for i in range(10)]}

    with patch.object(client, "_get", return_value=mock_data):
        result = client._fetch_recently_played()

    assert len(result) == 10


def test_fetch_top_artists_all_time_ranges(client):
    """_fetch_top_artists fetches short, medium, and long term."""
    def fresh_response(*args, **kwargs):
        # Return a new dict on each call to avoid mutation side effects
        return {"items": [{"id": "artist1", "name": "Artist One"}]}

    with patch.object(client, "_get", side_effect=fresh_response):
        result = client._fetch_top_artists()

    # 3 time ranges × 1 artist each = 3 records
    assert len(result) == 3
    # Each item is tagged with its time_range
    time_ranges = {item["time_range"] for item in result}
    assert time_ranges == {"short_term", "medium_term", "long_term"}


def test_fetch_top_tracks_all_time_ranges(client):
    """_fetch_top_tracks fetches short, medium, and long term."""
    mock_data = {"items": [{"id": "track1"}, {"id": "track2"}]}

    with patch.object(client, "_get", return_value=mock_data):
        result = client._fetch_top_tracks()

    # 3 time ranges × 2 tracks = 6 records
    assert len(result) == 6


# ---------------------------------------------------------------------------
# _parse tests
# ---------------------------------------------------------------------------


def test_parse_returns_records_for_all_endpoints(client):
    """_parse returns records tagged with correct endpoint names."""
    mock_albums = {"items": [{"album": {"id": "a1"}}], "next": None}
    mock_played = {"items": [{"track": {"id": "t1"}}]}
    mock_artists = {"items": [{"id": "ar1"}]}
    mock_tracks = {"items": [{"id": "tr1"}]}

    side_effects = [mock_albums, mock_played, mock_artists, mock_artists, mock_artists,
                    mock_tracks, mock_tracks, mock_tracks]

    with patch.object(client, "_get", side_effect=side_effects):
        records = client._parse()

    endpoints = {r["endpoint"] for r in records}
    assert "saved_albums" in endpoints
    assert "recently_played" in endpoints
    assert "top_artists" in endpoints
    assert "top_tracks" in endpoints


def test_parse_continues_on_endpoint_failure(client):
    """_parse skips a failed endpoint and continues with the rest."""
    def side_effect(url, **kwargs):
        if "albums" in url:
            raise Exception("Simulated network error")
        return {"items": [{"id": "x1"}], "next": None}

    with patch.object(client, "_get", side_effect=side_effect):
        records = client._parse()

    # saved_albums failed, but other endpoints still returned data
    endpoints = {r["endpoint"] for r in records}
    assert "saved_albums" not in endpoints
    assert len(records) > 0


# ---------------------------------------------------------------------------
# _write_to_bronze tests
# ---------------------------------------------------------------------------


def test_write_to_bronze_creates_table(client):
    """_write_to_bronze creates raw_spotify table and inserts all records."""
    import duckdb
    from datetime import datetime, timezone

    records = [
        {
            "endpoint": "saved_albums",
            "fetched_at": "2026-01-01T00:00:00+00:00",
            "payload": "{'id': 'a1'}",
            "_source": "spotify",
            "_loaded_at": datetime.now(timezone.utc),
        }
    ]

    client._write_to_bronze(records)

    con = duckdb.connect(str(client.db_path))
    count = con.execute("SELECT COUNT(*) FROM raw_spotify").fetchone()[0]
    con.close()

    assert count == 1


def test_write_to_bronze_skips_on_empty(client, caplog):
    """_write_to_bronze logs a warning and skips writing when records is empty."""
    import logging

    with caplog.at_level(logging.WARNING):
        client._write_to_bronze([])

    assert "skipping" in caplog.text.lower()