# =============================================================================
# TasteBase — Multi-stage Dockerfile
#
# Stage 1 — builder  : installs all Python dependencies into /install
# Stage 2 — runtime  : lean production image for api + agent services
#
# Usage:
#   docker build --target runtime -t tastebase-api .
#
# Required environment variables at runtime:
#   DUCKDB_PATH=/app/data/warehouse.duckdb   (must be absolute)
#   ANTHROPIC_API_KEY=...
#   SPOTIFY_CLIENT_ID=...  (optional — enrichment only)
#   TRAKT_CLIENT_ID=...    (optional)
# =============================================================================


# -----------------------------------------------------------------------------
# Stage 1 — builder
# Installs Python dependencies into a prefix directory for clean copy.
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system build dependencies needed by some Python packages
# (e.g. duckdb native extensions, pyarrow).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first to leverage Docker layer caching.
# Dependencies are only re-installed when requirements.txt changes.
COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# -----------------------------------------------------------------------------
# Stage 2 — runtime
# Lean image: copies installed packages from builder, adds application source.
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed Python packages from the builder stage
COPY --from=builder /install /usr/local

# Copy the full application source (filtered by .dockerignore)
COPY . .

# Create persistent data directories.
# data/raw  — CSV exports (bind-mounted from host in docker-compose)
# data/      — warehouse.duckdb lives here (named volume in docker-compose)
RUN mkdir -p data/raw data/templates

# dbt requires the profiles directory to exist.
# In production the profile is read from transform/profiles.yml via --profiles-dir.
RUN mkdir -p /root/.dbt

# Expose the FastAPI port
EXPOSE 8000

# Healthcheck: polls the /health endpoint every 30s.
# Gives the container 10s to start before the first check.
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

# Default command: start the FastAPI backend with a single worker.
# Override in docker-compose for the agent service (chainlit run ...).
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]