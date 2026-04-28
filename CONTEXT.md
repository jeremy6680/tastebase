# CONTEXT.md — TasteBase

> **Personal AI-powered taste warehouse** — A full-stack data engineering project that
> centralizes a user's cultural preferences (music, books, manga, movies, series, anime)
> into a DuckDB warehouse, exposes them through a Vue 3 frontend, and makes them queryable
> via a LangGraph conversational agent.

---

## Project Overview

**Name:** TasteBase
**Repository:** https://github.com/jeremy6680/tastebase (public)
**Author:** Jeremy Marchandeau
**Blog:** web2data.jeremymarchandeau.com
**Status:** Deployed in production

### Production URLs

| Service         | URL                                                   |
| --------------- | ----------------------------------------------------- |
| Frontend (Vue)  | https://tastebase.jeremymarchandeau.com               |
| API (FastAPI)   | https://api.tastebase.jeremymarchandeau.com           |
| Agent (Chainlit)| https://agent.tastebase.jeremymarchandeau.com         |
| API health      | https://api.tastebase.jeremymarchandeau.com/health    |
| API docs        | https://api.tastebase.jeremymarchandeau.com/docs      |

### What it does

1. Ingests cultural taste data from multiple sources (CSV exports from Buddy+ apps,
   Goodreads, Letterboxd, Spotify API, Trakt.tv API)
2. Stores everything in DuckDB using a medallion architecture (bronze/silver/gold)
3. Deduplicates items across sources using canonical IDs (ISBN, IMDB, TMDB, Discogs)
4. Exposes a Vue 3 web UI for browsing, filtering, sorting, and rating items (1–5 stars)
5. Powers a LangGraph AI agent that answers natural-language questions
6. Visualises taste analytics in an Insights section (Chart.js, embedded in the frontend)

---

## Architecture

```
data/raw/           ← CSV exports (gitignored, user-supplied)
ingestion/          ← Python scripts: CSV loaders + API clients (Spotify, Trakt)
transform/          ← dbt-duckdb project (bronze → silver → gold)
agent/              ← LangGraph agent with SQL, rating, and recommendation tools
api/                ← FastAPI backend (single DuckDB access layer)
frontend/           ← Vue 3 + Vite SPA (browse + rate + insights)
docker-compose.yml          ← Local dev: api + agent
docker-compose.api.yml      ← Coolify production: tastebase-api
docker-compose.agent.yml    ← Coolify production: tastebase-agent
docs/               ← Project documentation
```

### Data Flow

```
[CSV files]  [Spotify API]  [Trakt.tv API]
      ↓              ↓              ↓
   Bronze layer (raw, no transformation)
      ↓ dbt models
   Silver layer (cleaned, typed, domain-tagged, deduplicated)
      ↓ dbt models
   Gold layer (unified_tastes, ratings, aggregates, taste profile)
           ↓
      FastAPI (api/)
      /   \
   Vue 3   LangGraph Agent
 frontend   (Chainlit UI)
```

---

## Deployment Architecture

```
Hetzner VPS (Coolify + Traefik)
├── tastebase-api    FastAPI + DuckDB volume   → docker-compose.api.yml
└── tastebase-agent  Chainlit + LangGraph      → docker-compose.agent.yml

Netlify (static)
└── tastebase-ui     Vue 3 frontend            → frontend/netlify.toml
```

**Key deployment rules:**
- `docker-compose.api.yml` and `docker-compose.agent.yml` must be at the **repo root**
  (Coolify resolves `context: .` from its internal working directory)
- `args: {}` in the `build:` block prevents Coolify from injecting `--build-arg` for
  all env vars, which would cause `docker buildx bake` to fail
- `tastebase-agent` must set `API_BASE_URL=https://api.tastebase.jeremymarchandeau.com`
  (the two Coolify apps are on isolated Docker networks — `http://api:8000` does not work)

---

## DuckDB Concurrency Model

DuckDB supports only one writer at a time. The API and the ingestion pipeline share the
same `warehouse.duckdb` file — to avoid lock conflicts:

1. `get_db()` opens in `read_only=True` (all GET endpoints)
2. `get_db_write()` opens in `read_only=False` (write endpoints only)
3. The ingestion pipeline writes to `data/tmp/warehouse.duckdb` (isolated subdirectory,
   same filename stem so dbt catalog name `warehouse` matches)
4. On success, `data/tmp/warehouse.duckdb` atomically replaces `data/warehouse.duckdb`
5. The lifespan `ensure_table` is skipped on first boot (file doesn't exist yet)

See DEC-036, DEC-037, DEC-038, DEC-039.

---

## Domain Taxonomy

Six content domains, each with its own silver model:

| Domain   | Sources                                      | Detection method                                        |
| -------- | -------------------------------------------- | ------------------------------------------------------- |
| `music`  | MusicBuddy CSV, Spotify API                  | `Content Type = Album`                                  |
| `book`   | BookBuddy CSV, Goodreads CSV                 | Category/Tags/Publisher heuristics                      |
| `manga`  | BookBuddy CSV, Goodreads CSV                 | Keywords: manga/manhwa/bande dessinée + publisher list  |
| `movie`  | MovieBuddy CSV, Letterboxd CSV, Trakt.tv API | `Content Type = Movie`, Trakt `type=movie`              |
| `series` | Trakt.tv API                                 | Trakt `type=show`, genre ≠ Anime                        |
| `anime`  | MovieBuddy CSV, Trakt.tv API                 | Genre contains "Anime" (known gap — see DEC-019)        |

---

## Source Schemas

### goodreads.csv
Key columns: `Book Id`, `Title`, `Author`, `ISBN`, `ISBN13`, `My Rating` (0–5),
`Year Published`, `Date Read`, `Date Added`, `Bookshelves`

### bookbuddy.csv
Key columns: `Title`, `Author`, `ISBN`, `Rating` (0.0–5.0 float), `Tags`, `Category`,
`Status`, `Genre`, `Publisher`

### letterboxd.csv
Key columns: `Date`, `Name`, `Year`, `Letterboxd URI`, `Rating` (0.5–5.0 by 0.5)

### moviebuddy.csv
Key columns: `Title`, `Content Type` (Movie/TV Show), `Genres`, `Release Year`,
`IMDB ID`, `TMDB ID`, `Rating` (0.0–5.0 float), `Date Added`, `Status`

### musicbuddy.csv
Key columns: `Title`, `Artist`, `Release Year`, `Genres`, `Rating` (0.0–5.0 float),
`Date Added`, `Discogs Release ID`, `UPC-EAN13`, `Content Type` (Album)

### Spotify API
Endpoints: recently played, saved albums, top artists, top tracks. No native rating.

### Trakt.tv API
Endpoints: watched movies, watched shows, ratings. Rating 1–10 → `CEIL(rating / 2.0)`.

---

## Rating System

- **Scale:** 1–5 stars (integers only)
- **NULL** = unrated (never store 0)
- **User ratings** set via the UI override imported ratings
- **Rating history** tracked in `mart_rating_events` (append-only audit trail)

---

## Gold Layer Schema

### `mart_unified_tastes`
id (SHA256), domain, source, source_id, title, creator, year, genres, cover_url,
external_ids (JSON), status, date_added, date_consumed, created_at, updated_at

### `mart_ratings` (incremental — user ratings survive dbt rebuilds)
id, item_id, rating (1–5), source (imported|user), rated_at, notes

### `mart_rating_events` (append-only)
id, item_id, old_rating, new_rating, changed_by, changed_at

### `mart_item_categories` (satellite, outside dbt DAG)
item_id (PK), domain, genre, sub_genre, updated_at

---

## Tech Stack

| Layer            | Technology                     |
| ---------------- | ------------------------------ |
| Language         | Python 3.12                    |
| Warehouse        | DuckDB                         |
| Transformation   | dbt-duckdb                     |
| API framework    | FastAPI                        |
| Agent framework  | LangGraph                      |
| Chat UI          | Chainlit                       |
| Frontend         | Vue 3 + Vite + Chart.js        |
| Containerization | Docker + docker-compose        |
| Backend deploy   | Coolify on Hetzner VPS         |
| Frontend deploy  | Netlify (static build)         |
| i18n             | FR (default) / EN              |

---

## Developer Commands (Makefile)

```bash
make install      # Install Python dependencies
make ingest       # Run all ingestion scripts
make seed         # Load dbt seeds
make transform    # Run dbt models (bronze → silver → gold)
make pipeline     # ingest + seed + transform (full refresh)
make api          # Start FastAPI backend (port 8000)
make agent        # Start Chainlit agent UI (port 8080)
make frontend     # Start Vue frontend dev server (port 5173)
make stack        # Start API + agent + frontend in parallel
make dev          # Start full stack via Docker Compose (production-like)
make test         # Run pytest
make lint         # Run ruff + mypy
```

---

## Environment Variables

### Backend (.env at project root)

```bash
# Database — must be absolute path
DUCKDB_PATH=/absolute/path/to/data/warehouse.duckdb

# App
APP_ENV=development        # development | production
APP_SECRET_KEY=
DEFAULT_LANGUAGE=fr        # fr | en
AGENT_MODEL=claude-sonnet-4-6

# LLM
ANTHROPIC_API_KEY=

# Spotify (enrichment only)
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_ACCESS_TOKEN=
SPOTIFY_REFRESH_TOKEN=
SPOTIFY_REDIRECT_URI=urn:ietf:wg:oauth:2.0:oob

# Trakt.tv (tokens expire every 90 days — refresh via OAuth flow)
TRAKT_CLIENT_ID=
TRAKT_CLIENT_SECRET=
TRAKT_ACCESS_TOKEN=
TRAKT_REFRESH_TOKEN=

# Cross-app URLs
TASTEBASE_LIBRARY_URL=https://tastebase.jeremymarchandeau.com
TASTEBASE_AGENT_URL=https://agent.tastebase.jeremymarchandeau.com
TASTEBASE_DASHBOARD_URL=https://tastebase.jeremymarchandeau.com/insights

# Production CORS (tastebase-api Coolify app)
FRONTEND_URL=https://tastebase.jeremymarchandeau.com

# Production agent (tastebase-agent Coolify app)
API_BASE_URL=https://api.tastebase.jeremymarchandeau.com
```

### Frontend (Netlify env vars)

```bash
VITE_API_BASE_URL=https://api.tastebase.jeremymarchandeau.com
VITE_AGENT_URL=https://agent.tastebase.jeremymarchandeau.com
VITE_DASHBOARD_URL=https://tastebase.jeremymarchandeau.com/insights
```

---

## Ingestion Workflow

1. User exports CSV from Buddy+/Goodreads/Letterboxd
2. Uploads via the Vue UI (`UploadModal`) or via `curl POST /ingest/upload`
3. API saves file to `data/raw/<canonical_name>.csv`
4. API triggers `run_ingestion.py` in a subprocess (writes to `data/tmp/warehouse.duckdb`)
5. API triggers `dbt run` in a subprocess (transforms `data/tmp/warehouse.duckdb`)
6. On success: `data/tmp/warehouse.duckdb` atomically replaces `data/warehouse.duckdb`
7. Gold layer refreshes; agent and frontend reflect updated data

---

## Key Design Decisions

See `DECISIONS.md` for full log. Summary of latest decisions:

- **DEC-035** — Evidence.dev removed; Insights integrated into Vue 3 (Chart.js); Coolify
  split into two apps; frontend on Netlify
- **DEC-036** — Lifespan skips `ensure_table` on first boot
- **DEC-037** — `get_db()` read-only; `get_db_write()` for write endpoints
- **DEC-038** — Ingestion writes to tmp db to avoid DuckDB write lock
- **DEC-039** — Tmp db uses same filename stem (`warehouse`) for dbt catalog compatibility

---

## References

- [dbt-duckdb docs](https://github.com/duckdb/dbt-duckdb)
- [LangGraph docs](https://langchain-ai.github.io/langgraph/)
- [Chainlit docs](https://docs.chainlit.io)
- [Trakt.tv API](https://trakt.docs.apiary.io)
- [Spotify Web API](https://developer.spotify.com/documentation/web-api)
- [Vue 3 docs](https://vuejs.org)
- [Chart.js docs](https://www.chartjs.org)
