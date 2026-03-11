# =============================================================================
# TasteBase — Multi-stage Dockerfile
# Stage 1: builder (installs dependencies)
# Stage 2: runtime (lean production image)
# =============================================================================

# --- Stage 1: builder --------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- Stage 2: runtime --------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Create data directories (warehouse + raw uploads are mounted as volumes)
RUN mkdir -p data/raw data/templates

# Default command: start the FastAPI backend
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]