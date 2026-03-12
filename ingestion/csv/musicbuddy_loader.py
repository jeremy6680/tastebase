"""MusicBuddy CSV loader for TasteBase bronze layer.

Reads the MusicBuddy export CSV and writes it as-is (modulo column
renaming) to the raw_musicbuddy table in DuckDB.

Expected file: data/raw/musicbuddy.csv
See docs/data-sources.md for export and rename instructions.
"""

import logging
from pathlib import Path

import pandas as pd

from ingestion.base_loader import BaseLoader

logger = logging.getLogger(__name__)

# Canonical path — must match docs/data-sources.md instructions
DEFAULT_FILE_PATH = Path("data/raw/musicbuddy.csv")

# Columns that must be present for the loader to proceed.
# These are the raw column names as they appear in the CSV header.
REQUIRED_COLUMNS = [
    "Title",
    "Artist",
    "Content Type",
    "Rating",
    "Date Added",
]

# Mapping from raw CSV column names to snake_case identifiers.
# Only columns we actively use downstream are explicitly mapped.
# All other columns are renamed mechanically via _snake_case_columns().
COLUMN_RENAME_MAP = {
    "Title": "title",
    "Artist": "artist",
    "Series": "series",
    "Volume": "volume",
    "Release Year": "release_year",
    "Original Release Year": "original_release_year",
    "Genres": "genres",
    "Styles": "styles",
    "Content Type": "content_type",
    "Media": "media",                          # e.g. CD, Vinyl, Cassette
    "Format": "format",
    "Rating": "rating",                        # float 0.0–5.0 (0.0 = unrated)
    "Date Added": "date_added",
    "Tags": "tags",
    "Condition": "condition",
    "Cover Condition": "cover_condition",
    "UPC-EAN13": "upc_ean13",                  # fallback dedup key
    "discogs Release ID": "discogs_release_id", # primary dedup key
    "Uploaded Image URL": "cover_url",
    "Wish List": "wish_list",
    "Previously Owned": "previously_owned",
    "Notes": "notes",
    "Purchase Date": "purchase_date",
    "Purchase Price": "purchase_price",
    "Language": "language",
    "Country": "country",
    "Labels": "labels",
    "Catalog Number": "catalog_number",
    "Length": "length_seconds",
    "Tracks": "tracks",
    "Quantity": "quantity",
    "Physical Location": "physical_location",
    "Category": "category",
}


class MusicBuddyLoader(BaseLoader):
    """Loader for the MusicBuddy CSV export.

    MusicBuddy is the primary music source in TasteBase. Spotify is
    enrichment-only. Ratings from this source always take precedence
    over Spotify data in the silver layer.

    The CSV contains one row per album with metadata from Discogs
    (genres, styles, performers, track listings) embedded as JSON
    strings in some columns. Those JSON columns are kept as raw strings
    in bronze — parsing them is the silver layer's responsibility.
    """

    def __init__(
        self,
        db_path: str | Path,
        file_path: str | Path = DEFAULT_FILE_PATH,
    ) -> None:
        """Initialize the MusicBuddy loader.

        Args:
            db_path: Path to the DuckDB warehouse file.
            file_path: Path to the MusicBuddy CSV export.
                Defaults to data/raw/musicbuddy.csv.
        """
        super().__init__(
            source_name="musicbuddy",
            file_path=file_path,
            db_path=db_path,
        )

    def validate(self) -> bool:
        """Check that the CSV file exists and contains the expected columns.

        Returns:
            True if the file is present and all required columns exist.
        """
        # Check file existence first — gives a clearer error than pandas
        if not self.file_path.exists():
            self.logger.error(
                "MusicBuddy CSV not found at '%s'. "
                "See docs/data-sources.md for export instructions.",
                self.file_path,
            )
            return False

        # Read only the header row to check columns cheaply
        try:
            header_df = pd.read_csv(self.file_path, nrows=0)
        except Exception as exc:
            self.logger.error(
                "Failed to read CSV header from '%s': %s",
                self.file_path,
                exc,
            )
            return False

        return self._check_required_columns(header_df, REQUIRED_COLUMNS)

    def _parse(self) -> pd.DataFrame:
        """Read and normalize the MusicBuddy CSV.

        Reads all rows, renames columns to snake_case, and returns the
        raw DataFrame. No type coercion or filtering is performed here —
        that is the silver layer's responsibility.

        Returns:
            DataFrame with renamed columns and all original rows intact.
        """
        df = pd.read_csv(
            self.file_path,
            dtype=str,        # read everything as string — no silent type coercion
            keep_default_na=False,  # keep empty strings as "", not NaN
        )

        self.logger.debug(
            "Read %d rows and %d columns from '%s'",
            len(df),
            len(df.columns),
            self.file_path.name,
        )

        # Apply explicit renames for known columns
        df = df.rename(columns=COLUMN_RENAME_MAP)

        # Mechanically snake_case any remaining columns not in the map
        df = self._snake_case_remaining_columns(df)

        return df

    def _snake_case_remaining_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert any remaining PascalCase / mixed-case column names to snake_case.

        Applied after COLUMN_RENAME_MAP so only unmapped columns are affected.
        This ensures no column name survives with spaces or capital letters.

        Args:
            df: DataFrame after explicit column renaming.

        Returns:
            DataFrame with all columns in snake_case.
        """
        already_renamed = set(COLUMN_RENAME_MAP.values())

        new_columns = {}
        for col in df.columns:
            if col in already_renamed:
                # Already explicitly renamed — leave it alone
                continue
            # Replace spaces and special chars with underscore, lowercase
            snake = (
                col.strip()
                .lower()
                .replace(" ", "_")
                .replace("-", "_")
                .replace("/", "_")
                .replace("(", "")
                .replace(")", "")
            )
            if snake != col:
                new_columns[col] = snake

        return df.rename(columns=new_columns)