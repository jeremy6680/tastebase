# =============================================================================
# TasteBase — Developer commands
# =============================================================================

# Load .env file and export all variables to the environment.
# This ensures dbt and Python scripts receive the correct env vars,
# including DUCKDB_PATH, API keys, etc.
#
# -include prevents Make from failing if .env does not exist yet.
-include .env
export

.PHONY: install ingest transform pipeline seed agent api dev test lint help

# Install Python dependencies
install:
	pip install -r requirements.txt

# Run all ingestion scripts (CSV + API → DuckDB bronze)
ingest:
	python -m ingestion.run_ingestion

# Load dbt seeds (manga_publishers, domain_mapping)
seed:
	cd transform && dbt seed

# Run dbt transformations (bronze → silver → gold)
transform:
	cd transform && dbt run

# Full pipeline refresh: ingest + seed + transform
pipeline: ingest seed transform

# Start the Chainlit agent UI
agent:
	chainlit run agent/app.py --port 8080

# Start the FastAPI backend
api:
	uvicorn api.main:app --reload --port 8000

# Start the full stack via Docker Compose
dev:
	docker compose up --build

# Run the test suite
test:
	pytest tests/ -v

# Run linting and type checking
lint:
	ruff check .
	mypy .

# Show available commands
help:
	@echo ""
	@echo "TasteBase — available commands"
	@echo "------------------------------"
	@echo "  make install    Install Python dependencies"
	@echo "  make ingest     Run all ingestion scripts"
	@echo "  make seed       Load dbt seeds"
	@echo "  make transform  Run dbt models (bronze → silver → gold)"
	@echo "  make pipeline   Full refresh (ingest + seed + transform)"
	@echo "  make agent      Start Chainlit agent UI (port 8080)"
	@echo "  make api        Start FastAPI backend (port 8000)"
	@echo "  make dev        Start full stack via Docker Compose"
	@echo "  make test       Run pytest"
	@echo "  make lint       Run ruff + mypy"
	@echo ""