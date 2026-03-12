"""Tests for MusicBuddyLoader.

Covers validation, parsing, and DuckDB write behavior using
minimal in-memory CSV fixtures — no dependency on data/raw/.
"""

import duckdb
import pytest

from ingestion.csv.musicbuddy_loader import MusicBuddyLoader

# Minimal CSV with only the required columns + a few key ones
VALID_CSV = """Title,Artist,Content Type,Rating,Date Added,discogs Release ID,UPC-EAN13,Genres,Media,Uploaded Image URL
Foo Album,Some Band,Album,4.000000,2023/01/15 10:00:00.000,123456,0123456789012,Rock,CD,https://example.com/cover.jpg
Bar Album,Other Artist,Album,0.000000,2023/02/20 11:00:00.000,789012,,Punk,,
"""

MISSING_COLUMN_CSV = """Title,Artist,Genres
Foo Album,Some Band,Rock
"""


class TestMusicBuddyLoaderValidate:
    """Tests for MusicBuddyLoader.validate()."""

    def test_validate_returns_false_when_file_missing(self, tmp_db, tmp_path):
        """validate() returns False if the CSV file does not exist."""
        loader = MusicBuddyLoader(
            db_path=tmp_db,
            file_path=tmp_path / "nonexistent.csv",
        )
        assert loader.validate() is False

    def test_validate_returns_false_when_required_columns_missing(self, tmp_db, tmp_csv):
        """validate() returns False if required columns are absent."""
        path = tmp_csv("musicbuddy.csv", MISSING_COLUMN_CSV)
        loader = MusicBuddyLoader(db_path=tmp_db, file_path=path)
        assert loader.validate() is False

    def test_validate_returns_true_for_valid_file(self, tmp_db, tmp_csv):
        """validate() returns True for a well-formed CSV."""
        path = tmp_csv("musicbuddy.csv", VALID_CSV)
        loader = MusicBuddyLoader(db_path=tmp_db, file_path=path)
        assert loader.validate() is True


class TestMusicBuddyLoaderParse:
    """Tests for MusicBuddyLoader._parse()."""

    def test_parse_renames_columns_to_snake_case(self, tmp_db, tmp_csv):
        """_parse() renames raw CSV columns to snake_case identifiers."""
        path = tmp_csv("musicbuddy.csv", VALID_CSV)
        loader = MusicBuddyLoader(db_path=tmp_db, file_path=path)
        df = loader._parse()

        assert "title" in df.columns
        assert "artist" in df.columns
        assert "content_type" in df.columns
        assert "discogs_release_id" in df.columns
        assert "cover_url" in df.columns

        # Raw column names must not survive
        assert "Title" not in df.columns
        assert "discogs Release ID" not in df.columns
        assert "Uploaded Image URL" not in df.columns

    def test_parse_preserves_all_rows(self, tmp_db, tmp_csv):
        """_parse() keeps all rows including those with empty ratings."""
        path = tmp_csv("musicbuddy.csv", VALID_CSV)
        loader = MusicBuddyLoader(db_path=tmp_db, file_path=path)
        df = loader._parse()

        # CSV has 2 data rows — both must be kept (no filtering in bronze)
        assert len(df) == 2

    def test_parse_keeps_zero_ratings_as_string(self, tmp_db, tmp_csv):
        """_parse() does not convert or filter zero ratings — that's silver's job."""
        path = tmp_csv("musicbuddy.csv", VALID_CSV)
        loader = MusicBuddyLoader(db_path=tmp_db, file_path=path)
        df = loader._parse()

        ratings = df["rating"].tolist()
        assert "0.000000" in ratings  # zero rating preserved as-is


class TestMusicBuddyLoaderLoad:
    """Tests for MusicBuddyLoader.load() — full pipeline."""

    def test_load_writes_correct_row_count(self, tmp_db, tmp_csv):
        """load() returns the number of rows written to DuckDB."""
        path = tmp_csv("musicbuddy.csv", VALID_CSV)
        loader = MusicBuddyLoader(db_path=tmp_db, file_path=path)
        count = loader.load()

        assert count == 2

    def test_load_creates_bronze_table(self, tmp_db, tmp_csv):
        """load() creates the raw_musicbuddy table in DuckDB."""
        path = tmp_csv("musicbuddy.csv", VALID_CSV)
        loader = MusicBuddyLoader(db_path=tmp_db, file_path=path)
        loader.load()

        conn = duckdb.connect(str(tmp_db))
        tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
        assert "raw_musicbuddy" in tables
        conn.close()

    def test_load_injects_audit_columns(self, tmp_db, tmp_csv):
        """load() adds _source and _loaded_at columns to every row."""
        path = tmp_csv("musicbuddy.csv", VALID_CSV)
        loader = MusicBuddyLoader(db_path=tmp_db, file_path=path)
        loader.load()

        conn = duckdb.connect(str(tmp_db))
        row = conn.execute(
            "SELECT _source, _loaded_at FROM raw_musicbuddy LIMIT 1"
        ).fetchone()
        conn.close()

        assert row[0] == "musicbuddy"
        assert row[1] is not None  # _loaded_at was set

    def test_load_raises_on_missing_file(self, tmp_db, tmp_path):
        """load() raises ValueError when the CSV file does not exist."""
        loader = MusicBuddyLoader(
            db_path=tmp_db,
            file_path=tmp_path / "nonexistent.csv",
        )
        with pytest.raises(ValueError, match="Validation failed"):
            loader.load()

    def test_load_is_idempotent(self, tmp_db, tmp_csv):
        """load() can be run multiple times — always produces the same row count."""
        path = tmp_csv("musicbuddy.csv", VALID_CSV)
        loader = MusicBuddyLoader(db_path=tmp_db, file_path=path)

        count_first = loader.load()
        count_second = loader.load()

        assert count_first == count_second == 2