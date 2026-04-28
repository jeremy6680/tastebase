# TasteBase

> Personal AI-powered cultural taste warehouse — music, books, manga, movies, series, anime.

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![dbt](https://img.shields.io/badge/dbt-duckdb-orange?logo=dbt)](https://docs.getdbt.com)
[![DuckDB](https://img.shields.io/badge/DuckDB-latest-yellow)](https://duckdb.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Vue 3](https://img.shields.io/badge/Vue-3-41b883?logo=vue.js)](https://vuejs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

TasteBase aggregates your cultural consumption data from multiple apps into a single
[DuckDB](https://duckdb.org) warehouse, exposes it through an interactive Vue 3 frontend,
and makes it queryable via a [LangGraph](https://langchain-ai.github.io/langgraph/)
conversational agent.

**Live demo:** https://tastebase.jeremymarchandeau.com

---

## What it does

- **Ingest** CSV exports and API data from MusicBuddy, BookBuddy, Goodreads, MovieBuddy,
  Letterboxd, Spotify, and Trakt.tv
- **Transform** raw data through a medallion architecture (bronze → silver → gold) using dbt
- **Browse and rate** your entire cultural library from a single Vue 3 interface
- **Query** your taste profile in natural language via a LangGraph + Chainlit chat agent
- **Analyse** trends and patterns in the Insights section (Chart.js visualisations)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Data sources                                                        │
│  MusicBuddy · BookBuddy · Goodreads · MovieBuddy · Letterboxd        │
│  Spotify API · Trakt.tv API                                          │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ CSV exports + API calls
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  ingestion/  (Python)                                                │
│  One loader per source · Audit columns (_source, _loaded_at)         │
│  Writes to data/tmp/warehouse.duckdb (isolated from live API)        │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ atomic replace on success
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  DuckDB warehouse  (data/warehouse.duckdb)                           │
│                                                                      │
│  Bronze  raw_musicbuddy · raw_bookbuddy · raw_goodreads              │
│  (table) raw_moviebuddy · raw_letterboxd · raw_spotify · raw_trakt   │
│                                                                      │
│  Silver  stg_music · stg_books · stg_movies · stg_series · stg_anime │
│  (view)  Normalized · deduplicated · unified 1–5 rating scale        │
│                                                                      │
│  Gold    mart_unified_tastes · mart_ratings · mart_rating_events     │
│  (table) mart_top_rated · mart_taste_profile · mart_item_categories  │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  FastAPI  (api/)       │
              │  All reads + writes    │
              │  Pydantic schemas      │
              └────────┬───────────────┘
                       │
          ┌────────────┴─────────────┐
          ▼                          ▼
┌─────────────────────┐   ┌──────────────────────────┐
│  Vue 3 + Vite       │   │  LangGraph + Chainlit    │
│  (frontend/)        │   │  (agent/)                │
│  Browse · rate ·    │   │  Conversational queries  │
│  upload · insights  │   │  Natural language → SQL  │
└─────────────────────┘   └──────────────────────────┘
```

**Stack:** Python 3.12 · DuckDB · dbt-duckdb · FastAPI · Vue 3 + Vite · Chart.js · LangGraph · Chainlit

**Deployment:** FastAPI + Chainlit on Coolify/Hetzner · Vue 3 on Netlify

---

## Prerequisites

| Tool    | Minimum version | Notes                               |
| ------- | --------------- | ----------------------------------- |
| Python  | 3.12            | `python --version`                  |
| Node.js | 18              | Required for the frontend           |
| pip     | latest          | `pip install --upgrade pip`         |
| Git     | any             | —                                   |

---

## Local setup

### 1. Clone and install Python dependencies

```bash
git clone https://github.com/jeremy6680/tastebase.git
cd tastebase
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

```bash
# Required — must be an absolute path
DUCKDB_PATH=/absolute/path/to/tastebase/data/warehouse.duckdb

# LLM — required for the agent
ANTHROPIC_API_KEY=

# Spotify (optional — album cover enrichment only)
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_ACCESS_TOKEN=
SPOTIFY_REFRESH_TOKEN=

# Trakt.tv (optional — watched shows and movies)
# Tokens expire every 90 days — see docs/data-sources.md for refresh instructions
TRAKT_CLIENT_ID=
TRAKT_CLIENT_SECRET=
TRAKT_ACCESS_TOKEN=
TRAKT_REFRESH_TOKEN=
```

> ⚠️ `DUCKDB_PATH` **must be an absolute path**. dbt runs from `transform/` and resolves
> paths relative to that directory — a relative path will silently fail.

### 3. Install frontend dependencies

```bash
cd frontend && npm install && cd ..
```

---

## Importing your data

TasteBase reads CSV exports from your apps. See [`docs/data-sources.md`](docs/data-sources.md)
for step-by-step export instructions.

### Option A — Via the web UI (recommended)

1. Start the API: `make api`
2. Start the frontend: `make frontend`
3. Click **"Importer un CSV"** in the sidebar
4. Select the source, drop your file, click **Importer**
5. The full pipeline runs automatically (ingestion + dbt)

### Option B — Via the API

```bash
curl -X POST http://localhost:8000/ingest/upload \
  -F "source=musicbuddy" \
  -F "file=@data/raw/musicbuddy.csv"
```

### Option C — Via the command line

```bash
cp ~/Downloads/MusicBuddy*.csv data/raw/musicbuddy.csv
set -a && source .env && set +a
python -m ingestion.run_ingestion
cd transform && dbt run && cd ..
```

Canonical filenames:

| App        | Expected filename         |
| ---------- | ------------------------- |
| MusicBuddy | `data/raw/musicbuddy.csv` |
| BookBuddy  | `data/raw/bookbuddy.csv`  |
| Goodreads  | `data/raw/goodreads.csv`  |
| MovieBuddy | `data/raw/moviebuddy.csv` |
| Letterboxd | `data/raw/letterboxd.csv` |

---

## Running locally

```bash
make api        # FastAPI backend      → http://localhost:8000
make frontend   # Vue 3 frontend       → http://localhost:5173
make agent      # Chainlit agent UI    → http://localhost:8080
make stack      # API + agent + frontend in parallel
make dev        # Full stack via Docker Compose
```

API docs: `http://localhost:8000/docs`

---

## Running with Docker (local)

```bash
cp .env.example .env   # fill in your values
docker compose up
```

Uses the root `docker-compose.yml` (api + agent, ports exposed locally).

---

## Project structure

```
tastebase/
├── ingestion/              Python loaders (CSV + Spotify + Trakt → bronze)
├── transform/              dbt-duckdb project (bronze → silver → gold)
├── api/                    FastAPI backend (single DuckDB access layer)
├── frontend/               Vue 3 + Vite SPA (browse, rate, insights)
├── agent/                  LangGraph agent + Chainlit UI
├── data/
│   ├── raw/                CSV exports (gitignored)
│   ├── tmp/                Temp db during ingestion (gitignored)
│   └── warehouse.duckdb    (gitignored)
├── docker-compose.yml          Local dev (api + agent)
├── docker-compose.api.yml      Coolify: tastebase-api
├── docker-compose.agent.yml    Coolify: tastebase-agent
└── docs/                   Extended documentation
```

Full annotated tree: [`STRUCTURE.md`](STRUCTURE.md)

---

## Known limitations

| Area                      | Description                                                                                                                        |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **Anime detection**       | MovieBuddy exports TMDB genres ("Animation", not "Anime"). `stg_anime` returns 0 rows until a better signal is added. See DEC-019. |
| **Spotify rate limiting** | Spotify enforces ~24h extended rate limits. Ingestion skips Spotify gracefully when rate-limited.                                  |
| **Synchronous pipeline**  | CSV upload triggers the full pipeline synchronously. Run with `--workers 1` (DuckDB single-writer constraint).                     |
| **Trakt token expiry**    | Trakt OAuth tokens expire every 90 days. Refresh via the OAuth flow using `urn:ietf:wg:oauth:2.0:oob` redirect URI.               |
| **Hard delete**           | Deleting a dbt-managed item via the UI will cause it to reappear on the next pipeline run. By design — see DEC-029.                |

---

## Documentation

| File                                             | Content                                        |
| ------------------------------------------------ | ---------------------------------------------- |
| [`CONTEXT.md`](CONTEXT.md)                       | Architecture, stack, deployment, decisions     |
| [`STRUCTURE.md`](STRUCTURE.md)                   | Annotated folder/file tree                     |
| [`DECISIONS.md`](DECISIONS.md)                   | Architectural decision log (DEC-001 → DEC-039) |
| [`NEXT_STEPS.md`](NEXT_STEPS.md)                 | Project roadmap                                |
| [`docs/data-sources.md`](docs/data-sources.md)   | Export instructions per app                    |
| [`docs/csv-templates.md`](docs/csv-templates.md) | Template column reference                      |
| [`docs/deployment.md`](docs/deployment.md)       | Coolify + Hetzner deployment guide             |
| [`docs/contributing.md`](docs/contributing.md)   | How to contribute                              |

---

## Contributing

Contributions, issues, and feature requests are welcome.
See [`docs/contributing.md`](docs/contributing.md) for the full guide.

---

## License

[MIT](LICENSE)
