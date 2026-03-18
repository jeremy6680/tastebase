"""Spotify API client — fetches saved albums, recently played, top artists/tracks.

Writes raw data to the bronze layer (raw_spotify table) in DuckDB.
Inherits from BaseApiClient to guarantee consistent audit columns (_source, _loaded_at).
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any

import duckdb
import httpx
from dotenv import load_dotenv

from ingestion.base_api_client import BaseApiClient

load_dotenv()

logger = logging.getLogger(__name__)


class SpotifyClient(BaseApiClient):
    """Fetches data from the Spotify Web API and loads it into the bronze layer.

    Handles token refresh automatically when the access token expires.
    All four endpoints are fetched and written as a single unified table
    (raw_spotify) with an `endpoint` column to distinguish them.

    Attributes:
        client_id: Spotify application client ID.
        client_secret: Spotify application client secret.
        access_token: Current OAuth access token (may be refreshed at runtime).
        refresh_token: OAuth refresh token used to renew the access token.
        base_url: Base URL for the Spotify Web API.
        auth_url: URL for the Spotify token endpoint.
    """

    # Number of items to request per API page (max allowed by Spotify)
    _PAGE_LIMIT = 50

    def __init__(self, db_path: str) -> None:
        """Initializes the Spotify client from environment variables.

        Args:
            db_path: Path to the DuckDB database file.

        Raises:
            EnvironmentError: If any required environment variable is missing.
        """
        super().__init__(source_name="spotify", db_path=db_path)

        required_vars = [
            "SPOTIFY_CLIENT_ID",
            "SPOTIFY_CLIENT_SECRET",
            "SPOTIFY_ACCESS_TOKEN",
            "SPOTIFY_REFRESH_TOKEN",
        ]
        missing = [v for v in required_vars if not os.getenv(v)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        self.client_id: str = os.environ["SPOTIFY_CLIENT_ID"]
        self.client_secret: str = os.environ["SPOTIFY_CLIENT_SECRET"]
        self.access_token: str = os.environ["SPOTIFY_ACCESS_TOKEN"]
        self.refresh_token: str = os.environ["SPOTIFY_REFRESH_TOKEN"]
        self.base_url = "https://api.spotify.com/v1"
        self.auth_url = "https://accounts.spotify.com/api/token"

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _refresh_access_token(self) -> None:
        """Refreshes the Spotify access token using the stored refresh token.

        Updates self.access_token in place. Does not persist the new token
        to .env — the caller is responsible for updating the environment if
        long-term persistence is needed.

        Raises:
            httpx.HTTPStatusError: If the token refresh request fails.
        """
        import base64

        creds = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        response = httpx.post(
            self.auth_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30,
        )
        response.raise_for_status()
        self.access_token = response.json()["access_token"]
        logger.info("Spotify access token refreshed successfully.")

    def _auth_headers(self) -> dict[str, str]:
        """Returns the Authorization headers for an API request.

        Returns:
            Dictionary with the Bearer token Authorization header.
        """
        return {"Authorization": f"Bearer {self.access_token}"}

    def _get(self, url: str, params: dict | None = None) -> Any:
        """Makes an authenticated GET request, refreshing the token on 401.

        Retries automatically on 429 (rate limit) by waiting the duration
        specified in the Retry-After response header (default: 5 seconds).

        Args:
            url: Full URL to request.
            params: Optional query parameters.

        Returns:
            Parsed JSON response as a Python object.

        Raises:
            httpx.HTTPStatusError: If the request fails after token refresh
                or after exhausting rate limit retries.
        """
        import time

        max_retries = 3

        for attempt in range(max_retries):
            response = httpx.get(url, headers=self._auth_headers(), params=params, timeout=30)

            # Token expired — refresh and retry immediately
            if response.status_code == 401:
                logger.warning("Spotify token expired, refreshing...")
                self._refresh_access_token()
                response = httpx.get(url, headers=self._auth_headers(), params=params, timeout=30)

            # Rate limited — wait and retry, but cap the wait to avoid blocking forever
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                if retry_after > 60:
                    logger.warning(
                        f"Spotify rate limit retry_after={retry_after}s exceeds 60s cap "
                        f"— skipping Spotify ingestion until rate limit clears."
                    )
                    raise httpx.HTTPStatusError(
                        f"Rate limited for {retry_after}s — skipped",
                        request=response.request,
                        response=response,
                    )
                logger.warning(
                    f"Spotify rate limit hit — waiting {retry_after}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            return response.json()

        # All retries exhausted
        response.raise_for_status()

    # ------------------------------------------------------------------
    # Endpoint fetchers
    # ------------------------------------------------------------------

    def _fetch_saved_albums(self) -> list[dict[str, Any]]:
        """Fetches all albums saved in the user's Spotify library.

        Paginates through all results using the `next` cursor.

        Returns:
            List of raw album objects from the Spotify API.
        """
        results: list[dict[str, Any]] = []
        url = f"{self.base_url}/me/albums"
        params: dict[str, Any] = {"limit": self._PAGE_LIMIT, "offset": 0}

        while url:
            data = self._get(url, params=params)
            items = data.get("items", [])
            results.extend(items)
            url = data.get("next")
            params = {}
            logger.debug(f"Fetched {len(items)} saved albums (total: {len(results)})")

        logger.info(f"Total saved albums fetched: {len(results)}")
        return results

    def _fetch_recently_played(self) -> list[dict[str, Any]]:
        """Fetches the user's 50 most recently played tracks.

        Spotify limits this endpoint to the last 50 items — no pagination.

        Returns:
            List of raw play history objects from the Spotify API.
        """
        data = self._get(
            f"{self.base_url}/me/player/recently-played",
            params={"limit": self._PAGE_LIMIT},
        )
        items = data.get("items", [])
        logger.info(f"Total recently played tracks fetched: {len(items)}")
        return items

    def _fetch_top_artists(self) -> list[dict[str, Any]]:
        """Fetches the user's top artists across short, medium, and long term.

        Returns:
            List of raw artist objects tagged with their time_range.
        """
        results: list[dict[str, Any]] = []
        for time_range in ("short_term", "medium_term", "long_term"):
            data = self._get(
                f"{self.base_url}/me/top/artists",
                params={"limit": self._PAGE_LIMIT, "time_range": time_range},
            )
            for item in data.get("items", []):
                item["time_range"] = time_range
            results.extend(data.get("items", []))
            logger.debug(f"Fetched top artists ({time_range}): {len(data.get('items', []))}")

        logger.info(f"Total top artists fetched: {len(results)}")
        return results

    def _fetch_top_tracks(self) -> list[dict[str, Any]]:
        """Fetches the user's top tracks across short, medium, and long term.

        Returns:
            List of raw track objects tagged with their time_range.
        """
        results: list[dict[str, Any]] = []
        for time_range in ("short_term", "medium_term", "long_term"):
            data = self._get(
                f"{self.base_url}/me/top/tracks",
                params={"limit": self._PAGE_LIMIT, "time_range": time_range},
            )
            for item in data.get("items", []):
                item["time_range"] = time_range
            results.extend(data.get("items", []))
            logger.debug(f"Fetched top tracks ({time_range}): {len(data.get('items', []))}")

        logger.info(f"Total top tracks fetched: {len(results)}")
        return results

    # ------------------------------------------------------------------
    # BaseApiClient interface
    # ------------------------------------------------------------------

    def _parse(self) -> list[dict[str, Any]]:
        """Fetches all Spotify endpoints and returns a unified list of records.

        Each record includes:
        - endpoint: which Spotify API call produced this record
        - fetched_at: ISO 8601 UTC timestamp of the fetch
        - payload: raw API response object as string

        Returns:
            List of dicts ready for audit column injection.
        """
        fetched_at = datetime.now(timezone.utc).isoformat()
        records: list[dict[str, Any]] = []

        fetchers = [
            ("saved_albums", self._fetch_saved_albums),
            ("recently_played", self._fetch_recently_played),
            ("top_artists", self._fetch_top_artists),
            ("top_tracks", self._fetch_top_tracks),
        ]

        for endpoint_name, fetcher in fetchers:
            try:
                items = fetcher()
                for item in items:
                    records.append({
                        "endpoint": endpoint_name,
                        "fetched_at": fetched_at,
                        "payload": str(item),
                    })
            except Exception as exc:
                logger.error(f"Failed to fetch Spotify endpoint '{endpoint_name}': {exc}")
                continue

        logger.info(f"Total Spotify records prepared for bronze: {len(records)}")
        return records

    def _write_to_bronze(self, records: list[dict[str, Any]]) -> None:
        """Writes Spotify records to the raw_spotify bronze table in DuckDB.

        Args:
            records: List of dicts with audit columns already injected.
        """
        if not records:
            logger.warning("No Spotify records to write — skipping.")
            return

        import pandas as pd

        df = pd.DataFrame(records)

        con = duckdb.connect(str(self.db_path))
        try:
            con.execute("""
                CREATE OR REPLACE TABLE raw_spotify (
                    endpoint     VARCHAR NOT NULL,
                    fetched_at   VARCHAR,
                    payload      VARCHAR,
                    _source      VARCHAR NOT NULL,
                    _loaded_at   TIMESTAMPTZ NOT NULL
                )
            """)
            con.execute("INSERT INTO raw_spotify SELECT * FROM df")
            count = con.execute("SELECT COUNT(*) FROM raw_spotify").fetchone()[0]
            logger.info(f"raw_spotify: {count} rows written to bronze.")
        finally:
            con.close()