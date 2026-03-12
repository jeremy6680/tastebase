"""Letterboxd CSV loader for TasteBase bronze layer.

Reads the Letterboxd ratings CSV and writes it to the raw_letterboxd
table in DuckDB. Letterboxd is a movies-only source — every row is
always in the movie domain.

Expected file: data/raw/letterboxd.csv
  (renamed from ratings.csv inside the Letterboxd export zip)
See docs/data-sources.md for export and rename instructions.
"""

import logging
from pathlib import Path

import pandas as pd

from ingestion.base_loader import BaseLoader

logger = logging.getLogger(__name__)

DEFAULT_FILE_PATH = Path("data/raw/letterboxd.csv")

# Letterboxd's ratings.csv has exactly 5 columns — all are required
REQUIRED_COLUMNS = [
    "Date",
    "Name",
    "Year",
    "Letterboxd URI",
    "Rating",
]

COLUMN_RENAME_MAP = {
    "Date": "date_added",          # date the rating was logged
    "Name": "title",               # movie title
    "Year": "release_year",        # release year
    "Letterboxd URI": "letterboxd_uri",  # unique URL; used as source_id
    "Rating": "rating",            # float 0.5–5.0 by 0.5 increments
}


class LetterboxdLoader(BaseLoader):
    """Loader for the Letterboxd ratings CSV export.

    Letterboxd is a secondary movie source, merged with MovieBuddy in
    the silver layer. Deduplication uses IMDB ID as the primary key
    (enriched via TMDB API in a future phase), falling back to
    title + release_year.

    The Letterboxd export is intentionally minimal (5 columns). It
    contains only rated films — unrated films in the watchlist are
    in a separate watchlist.csv which is not ingested by TasteBase.

    Rating scale: 0.5 to 5.0 in 0.5 increments. Normalized to 1–5
    integer in the silver layer via ROUND().
    """

    def __init__(
        self,
        db_path: str | Path,
        file_path: str | Path = DEFAULT_FILE_PATH,
    ) -> None:
        """Initialize the Letterboxd loader.

        Args:
            db_path: Path to the DuckDB warehouse file.
            file_path: Path to the Letterboxd ratings CSV.
                Defaults to data/raw/letterboxd.csv.
        """
        super().__init__(
            source_name="letterboxd",
            file_path=file_path,
            db_path=db_path,
        )

    def validate(self) -> bool:
        """Check that the CSV file exists and contains the expected columns.

        Returns:
            True if the file is present and all required columns exist.
        """
        if not self.file_path.exists():
            self.logger.error(
                "Letterboxd CSV not found at '%s'. "
                "See docs/data-sources.md for export and rename instructions.",
                self.file_path,
            )
            return False

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
        """Read and normalize the Letterboxd CSV.

        Letterboxd's CSV is clean and minimal — no complex columns,
        no embedded JSON, no encoding issues expected.

        Returns:
            DataFrame with renamed columns and all original rows intact.
        """
        df = pd.read_csv(
            self.file_path,
            dtype=str,
            keep_default_na=False,
        )

        self.logger.debug(
            "Read %d rows and %d columns from '%s'",
            len(df),
            len(df.columns),
            self.file_path.name,
        )

        # All 5 columns are explicitly mapped — no remaining columns to snake_case
        df = df.rename(columns=COLUMN_RENAME_MAP)

        return df