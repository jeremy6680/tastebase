"""BookBuddy CSV loader for TasteBase bronze layer.

Reads the BookBuddy export CSV and writes it to the raw_bookbuddy
table in DuckDB. BookBuddy contains both books and manga — domain
detection (book vs manga) is handled in the silver layer.

Expected file: data/raw/bookbuddy.csv
See docs/data-sources.md for export and rename instructions.
"""

import logging
from pathlib import Path

import pandas as pd

from ingestion.base_loader import BaseLoader

logger = logging.getLogger(__name__)

DEFAULT_FILE_PATH = Path("data/raw/bookbuddy.csv")

# Raw column names as they appear in the CSV header
REQUIRED_COLUMNS = [
    "Title",
    "Author",
    "Rating",
    "Date Added",
    "Category",
]

COLUMN_RENAME_MAP = {
    "Title": "title",
    "Original Title": "original_title",
    "Subtitle": "subtitle",
    "Series": "series",
    "Volume": "volume",
    "Author": "author",
    "Author (Last, First)": "author_last_first",
    "Illustrator": "illustrator",
    "Translator": "translator",
    "Publisher": "publisher",
    "Place of Publication": "place_of_publication",
    "Date Published": "date_published",
    "Year Published": "year_published",
    "Original Year Published": "original_year_published",
    "Edition": "edition",
    "Genre": "genre",
    "Summary": "summary",
    "Number of Pages": "number_of_pages",
    "Format": "format",
    "Language": "language",
    "Original Language": "original_language",
    "ISBN": "isbn",                    # fallback dedup key
    "Rating": "rating",                # float 0.0–5.0 (0.0 = unrated)
    "Status": "status",
    "Date Started": "date_started",
    "Date Finished": "date_finished",
    "Date Added": "date_added",
    "Tags": "tags",
    "Category": "category",            # used for manga detection in silver
    "Condition": "condition",
    "Physical Location": "physical_location",
    "Quantity": "quantity",
    "Wish List": "wish_list",
    "Previously Owned": "previously_owned",
    "Purchase Date": "purchase_date",
    "Purchase Price": "purchase_price",
    "Uploaded Image URL": "cover_url",
    "Google VolumeID": "google_volume_id",
    "Notes": "notes",
    "Recommended By": "recommended_by",
}


class BookBuddyLoader(BaseLoader):
    """Loader for the BookBuddy CSV export.

    BookBuddy is the primary source for books and manga. Domain detection
    (book vs manga) is deferred to the silver layer using the Category,
    Tags, Genre, and Publisher columns.

    Ratings are stored as raw float strings (e.g. "3.000000") and
    normalized to the 1–5 integer scale in the silver layer.
    """

    def __init__(
        self,
        db_path: str | Path,
        file_path: str | Path = DEFAULT_FILE_PATH,
    ) -> None:
        """Initialize the BookBuddy loader.

        Args:
            db_path: Path to the DuckDB warehouse file.
            file_path: Path to the BookBuddy CSV export.
                Defaults to data/raw/bookbuddy.csv.
        """
        super().__init__(
            source_name="bookbuddy",
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
                "BookBuddy CSV not found at '%s'. "
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
        """Read and normalize the BookBuddy CSV.

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
                .replace(",", "")
            )
            if snake != col:
                new_columns[col] = snake

        return df.rename(columns=new_columns)