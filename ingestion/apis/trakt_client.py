"""Trakt.tv API client — fetches watched movies, watched shows, and ratings.

Writes raw data to the bronze layer (raw_trakt table) in DuckDB.
Inherits from BaseApiClient to guarantee consistent audit columns (_source, _loaded_at).

Trakt API reference: https://trakt.docs.apiary.io
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


class TraktClient(BaseApiClient):
    """Fetches data from the Trakt.tv API and loads it into the bronze layer.

    Handles token refresh automatically when the access token expires (90 days).
    All endpoints are fetched and written as a single unified table (raw_trakt)
    with an `endpoint` column to distinguish record types.

    Trakt API requires:
    - `trakt-api-key` header (= Client ID) on every request
    - `Authorization: Bearer <access_token>` for user-specific endpoints
    - `trakt-api-version: 2` header on every request

    Attributes:
        client_id: Trakt application client ID.
        client_secret: Trakt application client secret.
        access_token: Current OAuth access token (may be refreshed at runtime).
        refresh_token: OAuth refresh token used to renew the access token.
        base_url: Base URL for the Trakt API.
        auth_url: URL for the Trakt token endpoint.
    """

    _PAGE_LIMIT = 100

    def __init__(self, db_path: str) -> None:
        """Initializes the Trakt client from environment variables.

        Args:
            db_path: Path to the DuckDB database file.

        Raises:
            EnvironmentError: If any required environment variable is missing.
        """
        super().__init__(source_name="trakt", db_path=db_path)

        required_vars = [
            "TRAKT_CLIENT_ID",
            "TRAKT_CLIENT_SECRET",
            "TRAKT_ACCESS_TOKEN",
            "TRAKT_REFRESH_TOKEN",
        ]
        missing = [v for v in required_vars if not os.getenv(v)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        self.client_id: str = os.environ["TRAKT_CLIENT_ID"]
        self.client_secret: str = os.environ["TRAKT_CLIENT_SECRET"]
        self.access_token: str = os.environ["TRAKT_ACCESS_TOKEN"]
        self.refresh_token: str = os.environ["TRAKT_REFRESH_TOKEN"]
        self.base_url = "https://api.trakt.tv"
        self.auth_url = "https://api.trakt.tv/oauth/token"

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _refresh_access_token(self) -> None:
        """Refreshes the Trakt access token using the stored refresh token.

        Trakt rotates the refresh token on each refresh — both tokens are updated.

        Raises:
            httpx.HTTPStatusError: If the token refresh request fails.
        """
        response = httpx.post(
            self.auth_url,
            json={
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        logger.info("Trakt access token refreshed successfully.")
        logger.warning(
            "Trakt tokens rotated — update TRAKT_ACCESS_TOKEN and "
            "TRAKT_REFRESH_TOKEN in your .env file with the new values."
        )

    def _auth_headers(self) -> dict[str, str]:
        """Returns the required headers for an authenticated Trakt API request.

        Returns:
            Dictionary of required HTTP headers.
        """
        return {
            "Content-Type": "application/json",
            "trakt-api-version": "2",
            "trakt-api-key": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
        }

    def _get(self, path: str, params: dict | None = None) -> Any:
        """Makes an authenticated GET request to the Trakt API.

        Refreshes the token and retries once on 401.

        Args:
            path: API path relative to base_url.
            params: Optional query parameters.

        Returns:
            Parsed JSON response as a Python object.

        Raises:
            httpx.HTTPStatusError: If the request fails after token refresh.
        """
        url = f"{self.base_url}{path}"
        response = httpx.get(url, headers=self._auth_headers(), params=params, timeout=30)

        if response.status_code == 401:
            logger.warning("Trakt token expired, refreshing...")
            self._refresh_access_token()
            response = httpx.get(url, headers=self._auth_headers(), params=params, timeout=30)

        response.raise_for_status()
        return response.json()

    def _get_paginated(self, path: str) -> list[dict[str, Any]]:
        """Fetches all pages from a paginated Trakt endpoint.

        Args:
            path: API path relative to base_url.

        Returns:
            Aggregated list of all items across all pages.
        """
        results: list[dict[str, Any]] = []
        page = 1

        while True:
            url = f"{self.base_url}{path}"
            params = {"page": page, "limit": self._PAGE_LIMIT}
            response = httpx.get(url, headers=self._auth_headers(), params=params, timeout=30)

            if response.status_code == 401:
                logger.warning("Trakt token expired during pagination, refreshing...")
                self._refresh_access_token()
                response = httpx.get(url, headers=self._auth_headers(), params=params, timeout=30)

            response.raise_for_status()
            items = response.json()
            results.extend(items)

            total_pages = int(response.headers.get("X-Pagination-Page-Count", 1))
            logger.debug(f"Trakt {path}: page {page}/{total_pages} ({len(items)} items)")

            if page >= total_pages:
                break
            page += 1

        logger.info(f"Trakt {path}: {len(results)} total items fetched.")
        return results

    # ------------------------------------------------------------------
    # Endpoint fetchers
    # ------------------------------------------------------------------

    def _fetch_watched_movies(self) -> list[dict[str, Any]]:
        """Fetches all movies the user has marked as watched on Trakt.

        Returns:
            List of raw watched movie objects from the Trakt API.
        """
        return self._get_paginated("/users/me/watched/movies")

    def _fetch_watched_shows(self) -> list[dict[str, Any]]:
        """Fetches all shows the user has marked as watched on Trakt.

        Returns:
            List of raw watched show objects from the Trakt API.
        """
        return self._get_paginated("/users/me/watched/shows")

    def _fetch_ratings_movies(self) -> list[dict[str, Any]]:
        """Fetches all movie ratings submitted by the user on Trakt.

        Trakt ratings are 1–10. Conversion to 1–5 happens at silver layer only.

        Returns:
            List of raw movie rating objects from the Trakt API.
        """
        return self._get_paginated("/users/me/ratings/movies")

    def _fetch_ratings_shows(self) -> list[dict[str, Any]]:
        """Fetches all show ratings submitted by the user on Trakt.

        Returns:
            List of raw show rating objects from the Trakt API.
        """
        return self._get_paginated("/users/me/ratings/shows")

    # ------------------------------------------------------------------
    # BaseApiClient interface
    # ------------------------------------------------------------------

    def _parse(self) -> list[dict[str, Any]]:
        """Fetches all Trakt endpoints and returns a unified list of records.

        Each record includes:
        - endpoint: which Trakt API call produced this record
        - fetched_at: ISO 8601 UTC timestamp of the fetch
        - payload: raw API response object as string

        Returns:
            List of dicts ready for audit column injection.
        """
        fetched_at = datetime.now(timezone.utc).isoformat()
        records: list[dict[str, Any]] = []

        fetchers = [
            ("watched_movies", self._fetch_watched_movies),
            ("watched_shows", self._fetch_watched_shows),
            ("ratings_movies", self._fetch_ratings_movies),
            ("ratings_shows", self._fetch_ratings_shows),
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
                logger.error(
                    f"Failed to fetch Trakt endpoint '{endpoint_name}': {exc}"
                )
                continue

        logger.info(f"Total Trakt records prepared for bronze: {len(records)}")
        return records

    def _write_to_bronze(self, records: list[dict[str, Any]]) -> None:
        """Writes Trakt records to the raw_trakt bronze table in DuckDB.

        Args:
            records: List of dicts with audit columns already injected.
        """
        if not records:
            logger.warning("No Trakt records to write — skipping.")
            return

        import pandas as pd

        df = pd.DataFrame(records)

        con = duckdb.connect(str(self.db_path))
        try:
            con.execute("""
                CREATE OR REPLACE TABLE raw_trakt (
                    endpoint     VARCHAR NOT NULL,
                    fetched_at   VARCHAR,
                    payload      VARCHAR,
                    _source      VARCHAR NOT NULL,
                    _loaded_at   TIMESTAMPTZ NOT NULL
                )
            """)
            con.execute("INSERT INTO raw_trakt SELECT * FROM df")
            count = con.execute("SELECT COUNT(*) FROM raw_trakt").fetchone()[0]
            logger.info(f"raw_trakt: {count} rows written to bronze.")
        finally:
            con.close()