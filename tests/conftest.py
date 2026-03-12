"""Shared pytest fixtures for TasteBase tests.

Provides reusable fixtures for temporary DuckDB databases and
minimal CSV files that mirror real source schemas.
"""

import pytest
import duckdb
from pathlib import Path


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Create a temporary DuckDB database file for each test.

    Uses pytest's built-in tmp_path fixture so the file is
    automatically cleaned up after each test.

    Args:
        tmp_path: pytest temporary directory (unique per test).

    Returns:
        Path to the temporary DuckDB file.
    """
    db_path = tmp_path / "test_warehouse.duckdb"
    # Touch the file so loaders can connect to it
    duckdb.connect(str(db_path)).close()
    return db_path


@pytest.fixture
def tmp_csv(tmp_path: Path):
    """Factory fixture for creating temporary CSV files.

    Returns a callable that writes content to a named CSV file
    in the test's temporary directory.

    Usage:
        def test_something(tmp_csv):
            path = tmp_csv("musicbuddy.csv", "Title,Artist\\nFoo,Bar")

    Returns:
        A function(filename, content) -> Path.
    """
    def _make_csv(filename: str, content: str) -> Path:
        path = tmp_path / filename
        path.write_text(content, encoding="utf-8")
        return path

    return _make_csv