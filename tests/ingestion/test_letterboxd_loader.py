"""Tests for LetterboxdLoader.

Letterboxd is the simplest loader (5 columns) — good smoke test
to verify the base pattern works end-to-end.
"""

import pytest

from ingestion.csv.letterboxd_loader import LetterboxdLoader

VALID_CSV = """Date,Name,Year,Letterboxd URI,Rating
2023-01-15,The Godfather,1972,https://letterboxd.com/film/the-godfather/,5.0
2023-02-10,Pulp Fiction,1994,https://letterboxd.com/film/pulp-fiction/,4.5
2023-03-01,Meh Movie,2010,https://letterboxd.com/film/meh-movie/,2.0
"""

MISSING_COLUMN_CSV = """Date,Name,Year
2023-01-15,The Godfather,1972
"""


class TestLetterboxdLoaderValidate:

    def test_returns_false_for_missing_file(self, tmp_db, tmp_path):
        loader = LetterboxdLoader(db_path=tmp_db, file_path=tmp_path / "none.csv")
        assert loader.validate() is False

    def test_returns_false_for_missing_columns(self, tmp_db, tmp_csv):
        path = tmp_csv("letterboxd.csv", MISSING_COLUMN_CSV)
        loader = LetterboxdLoader(db_path=tmp_db, file_path=path)
        assert loader.validate() is False

    def test_returns_true_for_valid_file(self, tmp_db, tmp_csv):
        path = tmp_csv("letterboxd.csv", VALID_CSV)
        loader = LetterboxdLoader(db_path=tmp_db, file_path=path)
        assert loader.validate() is True


class TestLetterboxdLoaderLoad:

    def test_load_returns_correct_count(self, tmp_db, tmp_csv):
        path = tmp_csv("letterboxd.csv", VALID_CSV)
        loader = LetterboxdLoader(db_path=tmp_db, file_path=path)
        assert loader.load() == 3

    def test_load_renames_columns(self, tmp_db, tmp_csv):
        path = tmp_csv("letterboxd.csv", VALID_CSV)
        loader = LetterboxdLoader(db_path=tmp_db, file_path=path)
        loader.load()

        import duckdb
        conn = duckdb.connect(str(tmp_db))
        cols = [col[0] for col in conn.execute(
            "SELECT * FROM raw_letterboxd LIMIT 0"
        ).description]
        conn.close()

        assert "title" in cols       # renamed from "Name"
        assert "release_year" in cols # renamed from "Year"
        assert "Name" not in cols     # raw name must not survive

    def test_load_includes_audit_columns(self, tmp_db, tmp_csv):
        path = tmp_csv("letterboxd.csv", VALID_CSV)
        loader = LetterboxdLoader(db_path=tmp_db, file_path=path)
        loader.load()

        import duckdb
        conn = duckdb.connect(str(tmp_db))
        row = conn.execute(
            "SELECT _source FROM raw_letterboxd LIMIT 1"
        ).fetchone()
        conn.close()

        assert row[0] == "letterboxd"