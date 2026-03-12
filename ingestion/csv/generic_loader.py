"""Generic CSV loader for TasteBase user-supplied template files.

Handles the standard TasteBase CSV templates located in data/templates/.
These templates are designed for users who don't use Buddy+, Goodreads,
or Letterboxd — they fill in a standardized CSV instead.

Template files follow a naming convention that encodes the domain:
    template_music.csv   → domain: music
    template_books.csv   → domain: book
    template_manga.csv   → domain: manga
    template_movies.csv  → domain: movie
    template_series.csv  → domain: series
    template_anime.csv   → domain: anime

Expected files: data/templates/template_{domain}.csv
See docs/csv-templates.md for column reference per domain.
"""

import logging
from pathlib import Path

import pandas as pd

from ingestion.base_loader import BaseLoader

logger = logging.getLogger(__name__)

# Maps template filename stems to their canonical domain name
DOMAIN_FROM_FILENAME: dict[str, str] = {
    "template_music": "music",
    "template_books": "book",
    "template_manga": "manga",
    "template_movies": "movie",
    "template_series": "series",
    "template_anime": "anime",
}

# Columns present in every template regardless of domain
COMMON_REQUIRED_COLUMNS = [
    "title",
    "creator",
    "year",
    "rating",
    "status",
    "date_added",
]


class GenericLoader(BaseLoader):
    """Loader for user-supplied TasteBase CSV template files.

    Unlike source-specific loaders, this loader accepts any template
    file and infers the domain from the filename. Column names in
    template files are already snake_case — no renaming is needed.

    The resulting bronze table is named raw_template_{domain}, e.g.
    raw_template_music, raw_template_manga, etc.

    Attributes:
        domain: The content domain inferred from the filename.
    """

    def __init__(
        self,
        file_path: str | Path,
        db_path: str | Path,
    ) -> None:
        """Initialize the generic loader from a template file path.

        The domain and table name are inferred from the filename stem.
        For example, data/templates/template_manga.csv produces:
            domain     = "manga"
            table_name = "raw_template_manga"

        Args:
            file_path: Path to the template CSV file.
            db_path: Path to the DuckDB warehouse file.

        Raises:
            ValueError: If the filename does not match a known template.
        """
        file_path = Path(file_path)
        stem = file_path.stem  # e.g. "template_manga"

        if stem not in DOMAIN_FROM_FILENAME:
            raise ValueError(
                f"Unknown template filename '{file_path.name}'. "
                f"Expected one of: {list(DOMAIN_FROM_FILENAME.keys())}. "
                "See docs/csv-templates.md for naming conventions."
            )

        self.domain = DOMAIN_FROM_FILENAME[stem]

        super().__init__(
            source_name=f"template_{self.domain}",
            file_path=file_path,
            db_path=db_path,
        )

    def validate(self) -> bool:
        """Check that the template file exists and has the required columns.

        Returns:
            True if the file is present and all common columns exist.
        """
        if not self.file_path.exists():
            self.logger.error(
                "Template CSV not found at '%s'. "
                "See docs/csv-templates.md for the expected format.",
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

        return self._check_required_columns(header_df, COMMON_REQUIRED_COLUMNS)

    def _parse(self) -> pd.DataFrame:
        """Read the template CSV.

        Template columns are already in snake_case — no renaming needed.
        A _domain column is added to make the domain explicit in bronze,
        since all template tables share the same column structure.

        Returns:
            DataFrame with all template columns and an added _domain column.
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

        # Make the domain explicit as a column — useful when querying bronze
        df.insert(0, "_domain", self.domain)

        return df