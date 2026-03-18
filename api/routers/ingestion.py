# api/routers/ingestion.py

"""
Ingestion trigger endpoints.

POST /ingest/           — trigger the full pipeline (CSV files must already be in data/raw/)
POST /ingest/upload     — upload a CSV file for a given source, then run the full pipeline
GET  /ingest/sources    — list all supported sources with file presence status

Both write operations run synchronously. A background task queue (Celery, ARQ) would
be the right v2 approach if ingestion time becomes a UX problem.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# Project root is two levels up from this file (api/routers/ingestion.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRANSFORM_DIR = PROJECT_ROOT / "transform"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

# Canonical source → expected filename mapping (DEC-014)
SOURCES: dict[str, dict] = {
    "musicbuddy": {
        "label": "MusicBuddy",
        "filename": "musicbuddy.csv",
        "domain": "music",
    },
    "bookbuddy": {
        "label": "BookBuddy",
        "filename": "bookbuddy.csv",
        "domain": "book / manga",
    },
    "goodreads": {
        "label": "Goodreads",
        "filename": "goodreads.csv",
        "domain": "book / manga",
    },
    "moviebuddy": {
        "label": "MovieBuddy",
        "filename": "moviebuddy.csv",
        "domain": "movie / anime",
    },
    "letterboxd": {
        "label": "Letterboxd",
        "filename": "letterboxd.csv",
        "domain": "movie",
    },
}


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class IngestionResult(BaseModel):
    """Result of a full ingestion + transformation run."""

    status: str
    ingestion_stdout: str
    ingestion_returncode: int
    dbt_stdout: str
    dbt_returncode: int


class SourceStatus(BaseModel):
    """Presence status for a single CSV source."""

    key: str
    label: str
    filename: str
    domain: str
    present: bool


class SourcesResponse(BaseModel):
    """Response for GET /ingest/sources."""

    sources: list[SourceStatus]


class UploadResult(BaseModel):
    """Result of a CSV upload + ingestion run."""

    source: str
    filename: str
    ingestion: IngestionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_pipeline() -> IngestionResult:
    """Run run_ingestion.py then dbt run in sequence.

    Both commands inherit the current environment (including DUCKDB_PATH).

    Returns:
        IngestionResult: Return codes and combined stdout/stderr from both processes.

    Raises:
        HTTPException: 500 if either process binary is not found on PATH.
    """
    env = os.environ.copy()

    # Step 1: Python ingestion
    logger.info("Starting ingestion: run_ingestion.py")
    try:
        ingestion_result = subprocess.run(
            ["python", "-m", "ingestion.run_ingestion"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(PROJECT_ROOT),
        )
    except FileNotFoundError as exc:
        logger.error("Python not found: %s", exc)
        raise HTTPException(
            status_code=500, detail="Python interpreter not found."
        ) from exc

    logger.info(
        "Ingestion completed with returncode=%d", ingestion_result.returncode
    )

    # Step 2: dbt run
    logger.info("Starting dbt run")
    try:
        dbt_result = subprocess.run(
            ["dbt", "run"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(TRANSFORM_DIR),
        )
    except FileNotFoundError as exc:
        logger.error("dbt not found: %s", exc)
        raise HTTPException(
            status_code=500, detail="dbt command not found."
        ) from exc

    logger.info("dbt run completed with returncode=%d", dbt_result.returncode)

    return IngestionResult(
        status="ok" if dbt_result.returncode == 0 else "partial_failure",
        ingestion_stdout=ingestion_result.stdout + ingestion_result.stderr,
        ingestion_returncode=ingestion_result.returncode,
        dbt_stdout=dbt_result.stdout + dbt_result.stderr,
        dbt_returncode=dbt_result.returncode,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/sources", response_model=SourcesResponse)
def list_sources() -> SourcesResponse:
    """List all supported CSV sources with their file presence status.

    Returns:
        SourcesResponse: Each source with label, expected filename, domain,
            and whether the file currently exists in data/raw/.
    """
    statuses = []
    for key, meta in SOURCES.items():
        file_path = RAW_DATA_DIR / meta["filename"]
        statuses.append(
            SourceStatus(
                key=key,
                label=meta["label"],
                filename=meta["filename"],
                domain=meta["domain"],
                present=file_path.exists(),
            )
        )
    return SourcesResponse(sources=statuses)


@router.post("/", response_model=IngestionResult)
def trigger_ingestion() -> IngestionResult:
    """Run the full ingestion pipeline using CSV files already in data/raw/.

    Runs two subprocesses in sequence:
    1. `python -m ingestion.run_ingestion` — loads CSVs and API data into bronze
    2. `dbt run` (inside transform/) — rebuilds silver and gold models

    Returns:
        IngestionResult: Return codes and stdout from both processes.
    """
    return _run_pipeline()


@router.post("/upload", response_model=UploadResult)
async def upload_and_ingest(
    source: str = Form(..., description="Source key: musicbuddy | bookbuddy | goodreads | moviebuddy | letterboxd"),
    file: UploadFile = File(..., description="CSV file to upload"),
) -> UploadResult:
    """Upload a CSV file for a given source, save it to data/raw/, then run the pipeline.

    The file is saved using the canonical filename for the source (DEC-014),
    overwriting any previous version.

    Args:
        source: One of the supported source keys (musicbuddy, bookbuddy, etc.)
        file: The uploaded CSV file (must be text/csv or application/csv).

    Returns:
        UploadResult: Upload metadata + full pipeline IngestionResult.

    Raises:
        HTTPException: 400 if source key is unknown or file is not a CSV.
        HTTPException: 500 if the file cannot be saved.
    """
    # Validate source key
    if source not in SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source '{source}'. Valid sources: {', '.join(SOURCES)}",
        )

    # Validate MIME type (lenient: also accept octet-stream for some OS/browsers)
    allowed_content_types = {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
        "text/plain",
    }
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400,
            detail=f"File must be a CSV. Received content-type: {file.content_type}",
        )

    meta = SOURCES[source]
    canonical_filename = meta["filename"]
    destination = RAW_DATA_DIR / canonical_filename

    # Ensure data/raw/ exists
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Save the uploaded file
    logger.info("Saving uploaded file to %s", destination)
    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except OSError as exc:
        logger.error("Failed to save uploaded file: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"Could not save file: {exc}"
        ) from exc
    finally:
        await file.close()

    logger.info("File saved: %s (%d bytes)", destination, destination.stat().st_size)

    # Run the full pipeline
    ingestion_result = _run_pipeline()

    return UploadResult(
        source=source,
        filename=canonical_filename,
        ingestion=ingestion_result,
    )
