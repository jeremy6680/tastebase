# api/routers/ingestion.py

"""
Ingestion trigger endpoint.

POST /ingest  — runs run_ingestion.py then dbt run in sequence.
               Intended to be called after the user uploads a new CSV via the UI.

Both processes run synchronously in this version (v1). A background task
queue (Celery, ARQ) would be the right approach for v2 if ingestion time
becomes a UX problem.
"""

import logging
import os
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# Project root is two levels up from this file (api/routers/ingestion.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRANSFORM_DIR = PROJECT_ROOT / "transform"


class IngestionResult(BaseModel):
    """Result of a full ingestion + transformation run."""

    status: str
    ingestion_stdout: str
    ingestion_returncode: int
    dbt_stdout: str
    dbt_returncode: int


@router.post("/", response_model=IngestionResult)
def trigger_ingestion() -> IngestionResult:
    """Run the full ingestion pipeline: CSV/API loaders then dbt models.

    Runs two subprocesses in sequence:
    1. `python -m ingestion.run_ingestion` — loads CSVs and API data into bronze
    2. `dbt run` (inside transform/) — rebuilds silver and gold models

    Both commands inherit the current environment (including DUCKDB_PATH).

    Returns:
        IngestionResult: Return codes and stdout from both processes.

    Raises:
        HTTPException: 500 if either process fails to start.
    """
    env = os.environ.copy()

    # Step 1: run Python ingestion
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
        raise HTTPException(status_code=500, detail="Python interpreter not found.") from exc

    logger.info(
        "Ingestion completed with returncode=%d", ingestion_result.returncode
    )

    # Step 2: run dbt
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
        raise HTTPException(status_code=500, detail="dbt command not found.") from exc

    logger.info("dbt run completed with returncode=%d", dbt_result.returncode)

    return IngestionResult(
        status="ok" if dbt_result.returncode == 0 else "partial_failure",
        ingestion_stdout=ingestion_result.stdout + ingestion_result.stderr,
        ingestion_returncode=ingestion_result.returncode,
        dbt_stdout=dbt_result.stdout + dbt_result.stderr,
        dbt_returncode=dbt_result.returncode,
    )