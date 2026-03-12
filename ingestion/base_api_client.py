"""Abstract base class for all TasteBase API clients.

API clients differ from CSV loaders in three ways:
- No file_path: data comes from HTTP endpoints, not disk
- No validate(): credentials are checked in __init__ via EnvironmentError
- _parse() returns list[dict], not pd.DataFrame

This class provides the shared interface and audit column injection
without the CSV-specific constraints of BaseLoader.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


class BaseApiClient(ABC):
    """Abstract base class for all TasteBase API ingestion clients.

    Provides shared initialization (db_path, logging), audit column
    injection (_source, _loaded_at), and a consistent load() interface.

    Concrete subclasses must implement:
        _parse() -> list[dict]: fetch data from the API and return raw records
        _write_to_bronze(records): persist records to the DuckDB bronze table

    Attributes:
        source_name: Identifier for this source (e.g. "spotify", "trakt").
        db_path: Path to the DuckDB warehouse file.
        table_name: Bronze table name derived from source_name (raw_{source_name}).
        logger: Logger scoped to this client instance.
    """

    def __init__(self, source_name: str, db_path: str | Path) -> None:
        """Initializes the API client with source metadata and database path.

        Args:
            source_name: Identifier for this source (e.g. "spotify").
                Determines the bronze table name: raw_{source_name}.
            db_path: Path to the DuckDB warehouse file.
        """
        self.source_name = source_name
        self.db_path = Path(db_path)
        self.table_name = f"raw_{source_name}"
        self.logger = logging.getLogger(f"{__name__}.{source_name}")

    # ------------------------------------------------------------------
    # Abstract interface — must be implemented by every concrete client
    # ------------------------------------------------------------------

    @abstractmethod
    def _parse(self) -> list[dict[str, Any]]:
        """Fetch data from the API and return a list of raw records.

        Each record is a dict representing one API item. The endpoint
        and fetched_at fields should be included in each record.
        Do NOT add audit columns here (_source, _loaded_at) — they are
        injected automatically by load() before _write_to_bronze() is called.

        Returns:
            List of raw record dicts ready for audit column injection.
        """

    @abstractmethod
    def _write_to_bronze(self, records: list[dict[str, Any]]) -> None:
        """Persist records to the DuckDB bronze table.

        Called by load() after audit columns have been injected.
        Must use CREATE OR REPLACE TABLE for a full refresh on each run.

        Args:
            records: List of dicts including audit columns (_source, _loaded_at).
        """

    # ------------------------------------------------------------------
    # Shared implementation
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Run the full ingestion pipeline for this API source.

        Fetches data via _parse(), injects audit columns, then writes
        to the bronze layer via _write_to_bronze().

        Raises:
            EnvironmentError: If credentials are missing (raised in __init__).
            Exception: Any unhandled error from _parse() or _write_to_bronze().
        """
        self.logger.info("Starting API ingestion for source: %s", self.source_name)

        # Step 1 — Fetch from API
        records = self._parse()

        if not records:
            self.logger.warning(
                "Source '%s' returned no records — skipping write.", self.source_name
            )
            return

        self.logger.info(
            "Fetched %d records from '%s'", len(records), self.source_name
        )

        # Step 2 — Inject audit columns
        records = self._inject_audit_columns(records)

        # Step 3 — Write to bronze
        self._write_to_bronze(records)

        self.logger.info(
            "Ingestion complete for API source '%s'.", self.source_name
        )

    def _inject_audit_columns(
        self, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Inject _source and _loaded_at into every record.

        Mirrors the behavior of BaseLoader._inject_audit_columns() but
        operates on a list of dicts instead of a pandas DataFrame.

        Args:
            records: Raw records returned by _parse().

        Returns:
            Same records with _source and _loaded_at added to each dict.
        """
        loaded_at = datetime.now(timezone.utc)
        for record in records:
            record["_source"] = self.source_name
            record["_loaded_at"] = loaded_at
        self.logger.debug(
            "Audit columns injected: _source='%s', _loaded_at=%s",
            self.source_name,
            loaded_at,
        )
        return records