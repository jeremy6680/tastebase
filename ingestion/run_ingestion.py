"""Ingestion orchestrator for TasteBase.

Runs all CSV loaders in sequence and reports the result of each.
Called by `make ingest` or triggered via the FastAPI ingestion endpoint.

Usage:
    python -m ingestion.run_ingestion
    python -m ingestion.run_ingestion --db path/to/warehouse.duckdb
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from ingestion.csv.bookbuddy_loader import BookBuddyLoader
from ingestion.csv.generic_loader import DOMAIN_FROM_FILENAME, GenericLoader
from ingestion.csv.goodreads_loader import GoodreadsLoader
from ingestion.csv.letterboxd_loader import LetterboxdLoader
from ingestion.csv.moviebuddy_loader import MovieBuddyLoader
from ingestion.csv.musicbuddy_loader import MusicBuddyLoader

# Load environment variables from .env if present
load_dotenv()

# Configure logging for the orchestrator
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Default DB path — can be overridden via CLI arg or DUCKDB_PATH env var
DEFAULT_DB_PATH = Path(os.getenv("DUCKDB_PATH", "data/warehouse.duckdb"))

# Default templates directory
TEMPLATES_DIR = Path("data/templates")


def build_csv_loaders(db_path: Path) -> list:
    """Instantiate all CSV loaders for known sources.

    Each loader targets its canonical file path. If the file does not
    exist, the loader's validate() method will catch it gracefully.

    Args:
        db_path: Path to the DuckDB warehouse file.

    Returns:
        List of instantiated loader objects, ready to call .load() on.
    """
    return [
        MusicBuddyLoader(db_path=db_path),
        BookBuddyLoader(db_path=db_path),
        GoodreadsLoader(db_path=db_path),
        MovieBuddyLoader(db_path=db_path),
        LetterboxdLoader(db_path=db_path),
    ]


def build_template_loaders(db_path: Path) -> list:
    """Instantiate loaders for any user-supplied template CSVs found.

    Scans data/templates/ for files matching the known template naming
    convention. Missing template files are silently skipped — they are
    optional by design.

    Args:
        db_path: Path to the DuckDB warehouse file.

    Returns:
        List of GenericLoader instances for found template files.
    """
    loaders = []

    if not TEMPLATES_DIR.exists():
        logger.debug("Templates directory not found at '%s' — skipping.", TEMPLATES_DIR)
        return loaders

    for stem in DOMAIN_FROM_FILENAME:
        template_path = TEMPLATES_DIR / f"{stem}.csv"
        if template_path.exists():
            try:
                loaders.append(GenericLoader(file_path=template_path, db_path=db_path))
                logger.debug("Found template: %s", template_path.name)
            except ValueError as exc:
                # Should not happen since we iterate known stems, but be safe
                logger.warning("Skipping template '%s': %s", template_path.name, exc)

    return loaders


def run_ingestion(db_path: Path) -> bool:
    """Execute all CSV loaders and report results.

    Runs every loader regardless of individual failures so that one
    missing CSV does not block the others. Failures are logged and
    counted, but do not raise exceptions.

    Args:
        db_path: Path to the DuckDB warehouse file.

    Returns:
        True if all loaders succeeded, False if any loader failed.
    """
    logger.info("=" * 60)
    logger.info("TasteBase ingestion started")
    logger.info("Database: %s", db_path)
    logger.info("=" * 60)

    # Ensure the database directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    loaders = build_csv_loaders(db_path) + build_template_loaders(db_path)

    if not loaders:
        logger.warning("No loaders found. Nothing to ingest.")
        return True

    results: dict[str, int | Exception] = {}

    for loader in loaders:
        try:
            row_count = loader.load()
            results[loader.table_name] = row_count
        except Exception as exc:
            # Log the error but continue with remaining loaders
            logger.error(
                "Loader '%s' failed: %s",
                loader.table_name,
                exc,
                exc_info=True,
            )
            results[loader.table_name] = exc

    # Print summary
    logger.info("=" * 60)
    logger.info("Ingestion summary")
    logger.info("=" * 60)

    success_count = 0
    failure_count = 0

    for table_name, result in results.items():
        if isinstance(result, Exception):
            logger.error("  ✗ %-30s FAILED: %s", table_name, result)
            failure_count += 1
        else:
            logger.info("  ✓ %-30s %d rows", table_name, result)
            success_count += 1

    logger.info("-" * 60)
    logger.info(
        "Total: %d succeeded, %d failed",
        success_count,
        failure_count,
    )

    return failure_count == 0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="TasteBase ingestion orchestrator — runs all CSV loaders.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the DuckDB warehouse file.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = run_ingestion(db_path=args.db)
    sys.exit(0 if success else 1)