# TasteBase

> Personal AI-powered cultural taste warehouse — music, books, manga, movies, series, anime.

TasteBase centralises your cultural consumption data from multiple apps (MusicBuddy, BookBuddy, Goodreads, MovieBuddy, Letterboxd, Spotify, Trakt.tv) into a single DuckDB warehouse, exposes it through an interactive Vue 3 dashboard, and makes it queryable via a LangGraph conversational agent.

---

## Architecture overview

```
CSV exports / APIs
    ↓ ingestion/ (Python)
    ↓ Bronze layer  — raw tables, one per source
    ↓ Silver layer  — cleaned, typed, deduplicated (dbt views)
    ↓ Gold layer    — analytical marts (dbt tables)
    ↓
    ├── FastAPI backend  (api/)       ← all reads/writes go here
    ├── Vue 3 frontend   (frontend/)  ← browse, rate, upload
    ├── LangGraph agent  (agent/)     ← conversational queries
    └── Evidence.dev     (dashboard/) ← read-only analytics
```

**Stack:** Python 3.12 · DuckDB · dbt-duckdb · FastAPI · Vue 3 + Vite · LangGraph · Chainlit · Evidence.dev

---

## Prerequisites

- Python 3.12+
- Node.js 18+
- A virtual environment tool (`venv`, `pyenv`, etc.)
- `dbt-duckdb` installed (included in `requirements.txt`)

---

## Local setup

### 1. Clone and install Python dependencies

```bash
git clone https://github.com/jeremy6680/tastebase.git
cd tastebase
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

```bash
# Required — must be an absolute path
DUCKDB_PATH=/absolute/path/to/tastebase/data/warehouse.duckdb

# Spotify (optional — enrichment only)
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_ACCESS_TOKEN=
SPOTIFY_REFRESH_TOKEN=

# Trakt.tv (optional)
TRAKT_CLIENT_ID=
TRAKT_CLIENT_SECRET=
TRAKT_ACCESS_TOKEN=
TRAKT_REFRESH_TOKEN=
```

> ⚠️ `DUCKDB_PATH` **must be an absolute path**. dbt runs from `transform/` and will fail silently with a relative path.

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Importing your data

TasteBase reads CSV exports from your apps and saves them to `data/raw/` under fixed canonical filenames.

### Option A — Via the web UI (recommended)

1. Start the API (see below)
2. Start the frontend dev server
3. Click **"Importer un CSV"** in the sidebar
4. Select the source (e.g. MusicBuddy), drop your exported CSV, click **Importer**
5. The pipeline runs automatically: ingestion + dbt run

The uploaded file is saved under the canonical name automatically — **no renaming needed**.

### Option B — Via the command line

Copy your exports to `data/raw/` using the canonical filenames:

| App        | Expected filename          |
| ---------- | -------------------------- |
| MusicBuddy | `data/raw/musicbuddy.csv`  |
| BookBuddy  | `data/raw/bookbuddy.csv`   |
| Goodreads  | `data/raw/goodreads.csv`   |
| MovieBuddy | `data/raw/moviebuddy.csv`  |
| Letterboxd | `data/raw/letterboxd.csv`  |

```bash
# Example: copy a MusicBuddy export
cp ~/Downloads/MusicBuddy\ 2026-03-05\ 144228.csv data/raw/musicbuddy.csv
```

Then run the ingestion pipeline:

```bash
# Load all CSV files and API sources into the bronze layer
set -a && source .env && set +a
python -m ingestion.run_ingestion

# Rebuild silver and gold layers
cd transform
dbt run
cd ..
```

### Option C — Via the API directly

```bash
# Upload a CSV file and trigger the full pipeline in one call
curl -X POST http://localhost:8000/ingest/upload \
  -F "source=letterboxd" \
  -F "file=@/path/to/your/letterboxd.csv"

# Check which sources have files present in data/raw/
curl http://localhost:8000/ingest/sources

# Trigger the pipeline without uploading (files must already be in data/raw/)
curl -X POST http://localhost:8000/ingest/
```

> ⚠️ The pipeline runs **synchronously**. Large datasets or slow API calls (Trakt has 300+ items) can take 1–2 minutes. The request will not return until the pipeline completes.

---

## Running locally

### Start the FastAPI backend

```bash
set -a && source .env && set +a

# Single worker (for development — API blocked during pipeline runs)
uvicorn api.main:app --reload

# Multiple workers (recommended when testing CSV upload)
uvicorn api.main:app --workers 4
```

API available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Start the Vue 3 frontend

```bash
cd frontend
npm run dev
```

Frontend available at `http://localhost:5173`. The Vite dev server proxies `/api/*` requests to `http://localhost:8000`.

### Start the LangGraph agent (Chainlit)

```bash
set -a && source .env && set +a
chainlit run agent/app.py
```

Agent UI available at `http://localhost:8080`.

### Start the Evidence.dev dashboard

```bash
# Sync the warehouse file and start the dev server
make dashboard-sync
cd dashboard
npm run dev
```

Dashboard available at `http://localhost:3000`.

---

## Full pipeline (command line)

```bash
# 1. Load all sources into bronze
set -a && source .env && set +a
python -m ingestion.run_ingestion

# 2. Rebuild silver + gold
cd transform
dbt run

# 3. Run schema tests
dbt test
```

---

## Project structure

See [`STRUCTURE.md`](STRUCTURE.md) for the full annotated file tree.

Key directories:

| Path           | Purpose                                      |
| -------------- | -------------------------------------------- |
| `data/raw/`    | CSV exports (gitignored)                     |
| `ingestion/`   | Python loaders: CSV + Spotify + Trakt        |
| `transform/`   | dbt-duckdb project (bronze → silver → gold)  |
| `api/`         | FastAPI backend                              |
| `frontend/`    | Vue 3 + Vite SPA                             |
| `agent/`       | LangGraph agent + Chainlit UI                |
| `dashboard/`   | Evidence.dev analytics dashboard             |

---

## Known limitations

- **Anime detection:** MovieBuddy exports TMDB genres, which uses "Animation" not "Anime". The `stg_anime` model returns 0 rows until a better signal is implemented (see `DECISIONS.md` DEC-019).
- **Spotify rate limiting:** The Spotify API enforces extended rate limits (~23h). When rate-limited, Spotify ingestion is skipped automatically with a warning log. Trakt and CSV sources are unaffected.
- **Synchronous pipeline:** CSV upload triggers `run_ingestion.py` + `dbt run` synchronously. Other API requests queue behind it. Run uvicorn with `--workers 4` to avoid blocking the frontend during ingestion.
- **User ratings on re-upload:** User ratings set via the UI are preserved across pipeline rebuilds (`mart_ratings` uses incremental materialization). See `DECISIONS.md` DEC-030.

---

## Development decisions

All architectural decisions are logged in [`DECISIONS.md`](DECISIONS.md).  
The project roadmap is tracked in [`NEXT_STEPS.md`](NEXT_STEPS.md).

---

## License

MIT
