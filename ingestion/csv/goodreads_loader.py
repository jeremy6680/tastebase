"""Goodreads CSV loader for TasteBase bronze layer.

Reads the Goodreads library export CSV and writes it to the
raw_goodreads table in DuckDB. Like BookBuddy, Goodreads contains
both books and manga — domain detection is handled in silver.

Expected file: data/raw/goodreads.csv
See docs/data-sources.md for export and rename instructions.
"""

import logging
from pathlib import Path

import pandas as pd

from ingestion.base_loader import BaseLoader

logger = logging.getLogger(__name__)

DEFAULT_FILE_PATH = Path("data/raw/goodreads.csv")

REQUIRED_COLUMNS = [
    "Book Id",
    "Title",
    "Author",
    "My Rating",
    "Date Added",
    "Exclusive Shelf",
]

COLUMN_RENAME_MAP = {
    "Book Id": "book_id",              # Goodreads internal ID
    "Title": "title",
    "Author": "author",
    "Author l-f": "author_last_first",
    "Additional Authors": "additional_authors",
    "ISBN": "isbn",                    # may be empty; format: ="1234567890"
    "ISBN13": "isbn13",                # primary dedup key; format: ="9781234567890"
    "My Rating": "rating",             # integer 0–5 (0 = unrated)
    "Average Rating": "average_rating",
    "Publisher": "publisher",
    "Binding": "binding",              # e.g. Paperback, Hardcover, Kindle
    "Number of Pages": "number_of_pages",
    "Year Published": "year_published",
    "Original Publication Year": "original_publication_year",
    "Date Read": "date_read",
    "Date Added": "date_added",
    "Bookshelves": "bookshelves",      # user-defined shelves; used for manga detection
    "Bookshelves with positions": "bookshelves_with_positions",
    "Exclusive Shelf": "exclusive_shelf",  # read | currently-reading | to-read
    "My Review": "my_review",
    "Spoiler": "spoiler",
    "Private Notes": "private_notes",
    "Read Count": "read_count",
    "Owned Copies": "owned_copies",
}


class GoodreadsLoader(BaseLoader):
    """Loader for the Goodreads library export CSV.

    Goodreads is a secondary source for books and manga, merged with
    BookBuddy in the silver layer. Deduplication uses ISBN13 as the
    primary key, falling back to ISBN, then title + author.

    Note: Goodreads exports ISBN values wrapped in ="..." (e.g. ="9780000000000").
    This is a known Goodreads quirk — stripping the wrapper is handled
    in the silver layer, not here.

    Ratings use an integer 0–5 scale (0 = unrated), unlike the float
    scale used by the Buddy+ apps. Normalization to 1–5 happens in silver.
    """

    def __init__(
        self,
        db_path: str | Path,
        file_path: str | Path = DEFAULT_FILE_PATH,
    ) -> None:
        """Initialize the Goodreads loader.

        Args:
            db_path: Path to the DuckDB warehouse file.
            file_path: Path to the Goodreads CSV export.
                Defaults to data/raw/goodreads.csv.
        """
        super().__init__(
            source_name="goodreads",
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
                "Goodreads CSV not found at '%s'. "
                "See docs/data-sources.md for export instructions.",
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
        """Read and normalize the Goodreads CSV.

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

        df = df.rename(columns=COLUMN_RENAME_MAP)
        df = self._snake_case_remaining_columns(df)

        return df

    def _snake_case_remaining_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert any remaining column names to snake_case.

        Args:
            df: DataFrame after explicit column renaming.

        Returns:
            DataFrame with all columns in snake_case.
        """
        already_renamed = set(COLUMN_RENAME_MAP.values())

        new_columns = {}
        for col in df.columns:
            if col in already_renamed:
                continue
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