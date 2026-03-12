"""Tests for BaseLoader shared behavior.

Uses a minimal concrete subclass to test the shared methods
without depending on any specific source loader.
"""

import duckdb
import pandas as pd
import pytest

from ingestion.base_loader import BaseLoader


class MinimalLoader(BaseLoader):
    """Minimal concrete subclass for testing BaseLoader behavior."""

    def validate(self) -> bool:
        return self.file_path.exists()

    def _parse(self) -> pd.DataFrame:
        return pd.DataFrame({"title": ["Foo", "Bar"], "rating": ["3.0", "0.0"]})


class TestAuditColumns:
    """Tests for BaseLoader._inject_audit_columns()."""

    def test_inject_adds_source_column(self, tmp_db, tmp_path):
        """_inject_audit_columns() adds a _source column with the source name."""
        loader = MinimalLoader(
            source_name="test_source",
            file_path=tmp_path / "dummy.csv",
            db_path=tmp_db,
        )
        df = pd.DataFrame({"title": ["Foo"]})
        result = loader._inject_audit_columns(df)

        assert "_source" in result.columns
        assert result["_source"].iloc[0] == "test_source"

    def test_inject_adds_loaded_at_column(self, tmp_db, tmp_path):
        """_inject_audit_columns() adds a _loaded_at timestamp column."""
        loader = MinimalLoader(
            source_name="test_source",
            file_path=tmp_path / "dummy.csv",
            db_path=tmp_db,
        )
        df = pd.DataFrame({"title": ["Foo"]})
        result = loader._inject_audit_columns(df)

        assert "_loaded_at" in result.columns
        assert result["_loaded_at"].iloc[0] is not None

    def test_inject_does_not_mutate_original(self, tmp_db, tmp_path):
        """_inject_audit_columns() returns a copy — original DataFrame is unchanged."""
        loader = MinimalLoader(
            source_name="test_source",
            file_path=tmp_path / "dummy.csv",
            db_path=tmp_db,
        )
        df = pd.DataFrame({"title": ["Foo"]})
        loader._inject_audit_columns(df)

        assert "_source" not in df.columns


class TestCheckRequiredColumns:
    """Tests for BaseLoader._check_required_columns()."""

    def test_returns_true_when_all_columns_present(self, tmp_db, tmp_path):
        """Returns True when all required columns exist in the DataFrame."""
        loader = MinimalLoader("s", tmp_path / "f.csv", tmp_db)
        df = pd.DataFrame(columns=["title", "artist", "rating"])
        assert loader._check_required_columns(df, ["title", "rating"]) is True

    def test_returns_false_when_column_missing(self, tmp_db, tmp_path):
        """Returns False when a required column is absent."""
        loader = MinimalLoader("s", tmp_path / "f.csv", tmp_db)
        df = pd.DataFrame(columns=["title"])
        assert loader._check_required_columns(df, ["title", "rating"]) is False


class TestTableName:
    """Tests for BaseLoader table naming convention."""

    def test_table_name_uses_raw_prefix(self, tmp_db, tmp_path):
        """table_name is always raw_{source_name}."""
        loader = MinimalLoader("musicbuddy", tmp_path / "f.csv", tmp_db)
        assert loader.table_name == "raw_musicbuddy"