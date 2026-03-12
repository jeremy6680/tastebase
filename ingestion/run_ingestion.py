"""Ingestion orchestrator — runs all loaders in dependency order.

Execution order:
    1. CSV loaders (MusicBuddy, BookBuddy, Goodreads, MovieBuddy, Letterboxd)
    2. API clients (Spotify, Trakt)

Each loader writes its data to the DuckDB bronze layer independently.
A failed loader logs its error and is skipped — it does not abort the run.

Usage:
    python -m ingestion.run_ingestion
    # or via Makefile:
    make ingest
"""

import logging
import os
import sys
from pathlib import Path
from typing import NamedTuple

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DB_PATH = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
RAW_DIR = Path("data/raw")

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------


class LoaderResult(NamedTuple):
    """Outcome of a single loader run."""

    name: str
    success: bool
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_csv_loader(loader_class, csv_path: Path) -> LoaderResult:
    """Instantiates and runs a CSV loader, skipping gracefully if file is missing.

    Args:
        loader_class: The loader class to instantiate.
        csv_path: Expected path to the CSV file.

    Returns:
        LoaderResult with success/failure status and a descriptive message.
    """
    name = loader_class.__name__

    if not csv_path.exists():
        logger.warning(f"{name}: file not found at '{csv_path}' — skipping.")
        return LoaderResult(name=name, success=False, message=f"File not found: {csv_path}")

    try:
        # file_path is the correct kwarg name as defined in BaseLoader.__init__
        loader = loader_class(file_path=str(csv_path), db_path=DB_PATH)
        loader.load()
        return LoaderResult(name=name, success=True, message="OK")
    except Exception as exc:
        logger.error(f"{name} failed: {exc}", exc_info=True)
        return LoaderResult(name=name, success=False, message=str(exc))


def _run_api_client(client_class) -> LoaderResult:
    """Instantiates and runs an API client loader.

    Args:
        client_class: The API client class to instantiate.

    Returns:
        LoaderResult with success/failure status and a descriptive message.
    """
    name = client_class.__name__

    try:
        client = client_class(db_path=DB_PATH)
        client.load()
        return LoaderResult(name=name, success=True, message="OK")
    except EnvironmentError as exc:
        # Missing credentials — warn but do not crash the full run
        logger.warning(f"{name} skipped — missing credentials: {exc}")
        return LoaderResult(name=name, success=False, message=str(exc))
    except Exception as exc:
        logger.error(f"{name} failed: {exc}", exc_info=True)
        return LoaderResult(name=name, success=False, message=str(exc))


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def run_all() -> None:
    """Runs all ingestion loaders in dependency order.

    Order:
        Phase 1 — CSV loaders (always run first; data/raw/ files must exist)
        Phase 2 — API clients (run after CSV so bronze tables exist for merging)

    Logs a final summary table of all loader outcomes.
    Exits with code 1 if any loader failed, 0 if all succeeded.
    """
    logger.info("=" * 60)
    logger.info("TasteBase ingestion started")
    logger.info("=" * 60)

    results: list[LoaderResult] = []

    # ------------------------------------------------------------------
    # Phase 1 — CSV loaders
    # ------------------------------------------------------------------

    logger.info("--- Phase 1: CSV loaders ---")

    from ingestion.csv.musicbuddy_loader import MusicBuddyLoader
    from ingestion.csv.bookbuddy_loader import BookBuddyLoader
    from ingestion.csv.goodreads_loader import GoodreadsLoader
    from ingestion.csv.moviebuddy_loader import MovieBuddyLoader
    from ingestion.csv.letterboxd_loader import LetterboxdLoader

    csv_loaders = [
        (MusicBuddyLoader, RAW_DIR / "musicbuddy.csv"),
        (BookBuddyLoader, RAW_DIR / "bookbuddy.csv"),
        (GoodreadsLoader, RAW_DIR / "goodreads.csv"),
        (MovieBuddyLoader, RAW_DIR / "moviebuddy.csv"),
        (LetterboxdLoader, RAW_DIR / "letterboxd.csv"),
    ]

    for loader_class, csv_path in csv_loaders:
        result = _run_csv_loader(loader_class, csv_path)
        results.append(result)

    # ------------------------------------------------------------------
    # Phase 2 — API clients
    # ------------------------------------------------------------------

    logger.info("--- Phase 2: API clients ---")

    from ingestion.apis.spotify_client import SpotifyClient
    from ingestion.apis.trakt_client import TraktClient

    api_clients = [
        SpotifyClient,
        TraktClient,
    ]

    for client_class in api_clients:
        result = _run_api_client(client_class)
        results.append(result)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    logger.info("=" * 60)
    logger.info("Ingestion summary:")

    success_count = sum(1 for r in results if r.success)
    failure_count = len(results) - success_count

    for result in results:
        status = "OK" if result.success else "FAILED"
        logger.info(f"  [{status}] {result.name}: {result.message}")

    logger.info(f"  {success_count}/{len(results)} loaders succeeded.")
    logger.info("=" * 60)

    if failure_count > 0:
        logger.warning(f"{failure_count} loader(s) failed — check logs above.")
        sys.exit(1)

    logger.info("All loaders completed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    run_all()