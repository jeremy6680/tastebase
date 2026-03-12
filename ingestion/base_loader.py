"""Base loader for TasteBase ingestion layer.

All CSV and API loaders must inherit from BaseLoader and implement
the abstract methods defined here. This ensures a consistent interface
across all data sources and simplifies the ingestion orchestrator.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

import duckdb
import pandas as pd

# Module-level logger — each loader will use its own child logger
logger = logging.getLogger(__name__)


class BaseLoader(ABC):
    """Abstract base class for all TasteBase data loaders.

    Provides shared initialization logic (file path resolution, DuckDB
    connection, logging) and enforces a consistent interface via abstract
    methods that every concrete loader must implement.

    Audit columns added automatically to every bronze table:
        _source (str): Source identifier, e.g. "musicbuddy".
        _loaded_at (Timestamp): UTC timestamp of the ingestion run.

    Attributes:
        source_name: Human-readable identifier for the data source.
        file_path: Resolved path to the CSV file on disk.
        db_path: Path to the DuckDB database file.
        table_name: Name of the bronze table to write into.
        logger: Logger scoped to this loader instance.
    """

    def __init__(
        self,
        source_name: str,
        file_path: str | Path,
        db_path: str | Path,
    ) -> None:
        """Initialize the loader with source metadata and paths.

        Args:
            source_name: Identifier for this source (e.g. "musicbuddy").
                Used as the table suffix: raw_{source_name}.
            file_path: Path to the CSV file to ingest.
            db_path: Path to the DuckDB warehouse file.
        """
        self.source_name = source_name
        self.file_path = Path(file_path)
        self.db_path = Path(db_path)
        self.table_name = f"raw_{source_name}"

        # Scoped logger: e.g. "ingestion.base_loader.musicbuddy"
        self.logger = logging.getLogger(f"{__name__}.{source_name}")

    # ------------------------------------------------------------------
    # Abstract interface — must be implemented by every concrete loader
    # ------------------------------------------------------------------

    @abstractmethod
    def validate(self) -> bool:
        """Validate that the source file exists and has the expected columns.

        Returns:
            True if the file is valid and ready to load, False otherwise.
        """

    @abstractmethod
    def _parse(self) -> pd.DataFrame:
        """Read the source file and return a normalized DataFrame.

        Responsibilities:
        - Read the CSV with correct encoding and separator
        - Rename columns to snake_case English identifiers
        - Preserve all raw values — no type coercion, no filtering

        Do NOT add audit columns here (_source, _loaded_at).
        They are added automatically by load() after _parse() returns.

        Returns:
            A pandas DataFrame with renamed columns, ready for audit
            column injection and DuckDB insertion.
        """

    # ------------------------------------------------------------------
    # Shared implementation — available to all concrete loaders
    # ------------------------------------------------------------------

    def load(self) -> int:
        """Run the full ingestion pipeline for this source.

        Validates the source file, parses it into a DataFrame, injects
        audit columns, and writes the result to the bronze DuckDB table.
        The table is fully replaced on each run (no incremental logic).

        Returns:
            The number of rows successfully written to DuckDB.

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If validation fails or the parsed DataFrame is empty.
            duckdb.Error: If the DuckDB write operation fails.
        """
        self.logger.info("Starting ingestion for source: %s", self.source_name)

        # Step 1 — Validate before doing any work
        if not self.validate():
            raise ValueError(
                f"Validation failed for source '{self.source_name}'. "
                "Check that the file exists and has the expected columns. "
                "See docs/data-sources.md for export and rename instructions."
            )

        # Step 2 — Parse CSV into a DataFrame
        self.logger.info("Parsing file: %s", self.file_path)
        df = self._parse()

        if df.empty:
            raise ValueError(
                f"Source '{self.source_name}' produced an empty DataFrame. "
                "The file may be empty or malformed."
            )

        self.logger.info("Parsed %d rows from %s", len(df), self.file_path.name)

        # Step 3 — Inject audit columns
        # Done here in the base class so no concrete loader ever forgets them.
        df = self._inject_audit_columns(df)

        # Step 4 — Write to DuckDB bronze table
        row_count = self._write_to_duckdb(df)

        self.logger.info(
            "Ingestion complete for '%s': %d rows written to table '%s'",
            self.source_name,
            row_count,
            self.table_name,
        )

        return row_count

    def _inject_audit_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add traceability columns to every row before writing to bronze.

        These columns are prefixed with _ (dbt convention for technical
        metadata) and are never part of the original source data.

        Columns added:
            _source (str): Source identifier, e.g. "musicbuddy".
            _loaded_at (Timestamp): UTC timestamp of this ingestion run.

        Args:
            df: The parsed DataFrame returned by _parse().

        Returns:
            The same DataFrame with two additional columns prepended.
        """
        df = df.copy()  # avoid mutating the original DataFrame

        # Prepend audit columns so they appear first in the table schema
        df.insert(0, "_loaded_at", pd.Timestamp.now(tz="UTC"))
        df.insert(0, "_source", self.source_name)

        self.logger.debug(
            "Audit columns injected: _source='%s', _loaded_at=%s",
            self.source_name,
            df["_loaded_at"].iloc[0],
        )

        return df

    def _write_to_duckdb(self, df: pd.DataFrame) -> int:
        """Write a DataFrame to the bronze DuckDB table.

        Uses CREATE OR REPLACE TABLE to perform a full refresh on each run.
        This is intentional: bronze is immutable per ingestion run, and
        incremental logic does not belong at this layer.

        Args:
            df: The parsed and audit-enriched DataFrame to persist.

        Returns:
            The number of rows written.
        """
        self.logger.debug(
            "Writing %d rows to DuckDB table '%s' at '%s'",
            len(df),
            self.table_name,
            self.db_path,
        )

        with duckdb.connect(str(self.db_path)) as conn:
            conn.execute(
                f"CREATE OR REPLACE TABLE {self.table_name} AS SELECT * FROM df"
            )
            row_count = conn.execute(
                f"SELECT COUNT(*) FROM {self.table_name}"
            ).fetchone()[0]

        return row_count

    def _check_required_columns(
        self, df: pd.DataFrame, required: list[str]
    ) -> bool:
        """Check that all required columns are present in the DataFrame.

        Called from validate() in concrete loaders to avoid repeating
        this logic in every subclass.

        Args:
            df: The DataFrame to check (read with minimal parsing).
            required: List of column names that must be present in the
                raw CSV (before any renaming).

        Returns:
            True if all required columns are present, False otherwise.
        """
        missing = [col for col in required if col not in df.columns]
        if missing:
            self.logger.error(
                "Source '%s' is missing required columns: %s",
                self.source_name,
                missing,
            )
            return False
        return True