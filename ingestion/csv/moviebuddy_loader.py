"""MovieBuddy CSV loader for TasteBase bronze layer.

Reads the MovieBuddy export CSV and writes it to the raw_moviebuddy
table in DuckDB. MovieBuddy contains movies, series, and anime —
domain detection is handled in the silver layer using Content Type
and Genres columns.

Expected file: data/raw/moviebuddy.csv
See docs/data-sources.md for export and rename instructions.
"""

import logging
from pathlib import Path

import pandas as pd

from ingestion.base_loader import BaseLoader

logger = logging.getLogger(__name__)

DEFAULT_FILE_PATH = Path("data/raw/moviebuddy.csv")

REQUIRED_COLUMNS = [
    "Title",
    "Content Type",
    "Rating",
    "Date Added",
    "IMDB ID",
]

COLUMN_RENAME_MAP = {
    "Title": "title",
    "Original Title": "original_title",
    "TV Show Volume Title": "tv_show_volume_title",
    "Content Type": "content_type",    # "Movie" or "TV Show" — used for domain detection
    "Collection Type": "collection_type",
    "Series": "series",
    "Volume": "volume",
    "Runtime": "runtime",
    "Original Release Year": "original_release_year",
    "Release Year": "release_year",
    "Release Date": "release_date",
    "First Air Year": "first_air_year",
    "First Air Date": "first_air_date",
    "Last Air Year": "last_air_year",
    "Last Air Date": "last_air_date",
    "Number Of Seasons": "number_of_seasons",
    "Genres": "genres",                # used for anime detection: contains "Anime"
    "TV Creators": "tv_creators",
    "TV Networks": "tv_networks",
    "Directors": "directors",
    "Writers": "writers",
    "Cast": "cast",
    "Languages": "languages",
    "Summary": "summary",
    "Format": "format",
    "Film Rating": "film_rating",      # e.g. PG-13, R
    "IMDB ID": "imdb_id",              # primary dedup key for movies/series/anime
    "TMDB ID": "tmdb_id",              # fallback dedup key
    "UPC-EAN13": "upc_ean13",
    "Rating": "rating",                # float 0.0–5.0 (0.0 = unrated)
    "Status": "status",
    "Date Finished": "date_finished",
    "Date Added": "date_added",
    "Tags": "tags",
    "Category": "category",
    "Condition": "condition",
    "Physical Location": "physical_location",
    "Quantity": "quantity",
    "Wish List": "wish_list",
    "Previously Owned": "previously_owned",
    "Purchase Date": "purchase_date",
    "Purchase Price": "purchase_price",
    "Uploaded Image URL": "cover_url",
    "Notes": "notes",
    "Recommended By": "recommended_by",
    "TV Season": "tv_season",
    "Number Of Discs": "number_of_discs",
    "Production Countries": "production_countries",
}


class MovieBuddyLoader(BaseLoader):
    """Loader for the MovieBuddy CSV export.

    MovieBuddy is the primary source for movies and anime (TV Show +
    Anime genre). Series come from Trakt. Domain detection logic:
        - Content Type = "Movie"   → movie domain
        - Content Type = "TV Show" + Genres contains "Anime" → anime domain
        - Content Type = "TV Show" + no Anime genre → series domain (rare,
          prefer Trakt for series)

    All domain detection is deferred to the silver layer.
    """

    def __init__(
        self,
        db_path: str | Path,
        file_path: str | Path = DEFAULT_FILE_PATH,
    ) -> None:
        """Initialize the MovieBuddy loader.

        Args:
            db_path: Path to the DuckDB warehouse file.
            file_path: Path to the MovieBuddy CSV export.
                Defaults to data/raw/moviebuddy.csv.
        """
        super().__init__(
            source_name="moviebuddy",
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
                "MovieBuddy CSV not found at '%s'. "
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
        """Read and normalize the MovieBuddy CSV.

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