# STRUCTURE.md — TasteBase

> Annotated folder/file structure. Updated as new files are added.
> Each entry explains **what the file is** and **why it exists**.

---

```
tastebase/
│
├── .env.example                  # Environment variable template (never commit .env)
├── .gitignore                    # Ignores data/raw/, .env, __pycache__, .dbt/, etc.
├── .dockerignore                 # Excludes data/, .venv/, dashboard/, node_modules/ from Docker context
├── CONTEXT.md                    # Source of truth: architecture, stack, deployment, decisions
├── DECISIONS.md                  # Log of architectural and technical decisions with rationale
├── NEXT_STEPS.md                 # Ordered roadmap; checked items = done, unchecked = todo
├── STRUCTURE.md                  # This file — annotated project structure
├── README.md                     # Public-facing project overview and quickstart
├── Makefile                      # Developer commands (install, ingest, transform, etc.)
├── requirements.txt              # Python dependencies (pinned versions)
│
├── docker-compose.yml            # Local dev: api + agent (ports exposed, bind mounts)
├── docker-compose.api.yml        # Coolify production: tastebase-api (FastAPI + DuckDB volume)
├── docker-compose.agent.yml      # Coolify production: tastebase-agent (Chainlit, no volume)
│                                 # Both files are at repo root — Coolify requires this for
│                                 # context: . to resolve correctly in its build environment
├── Dockerfile                    # Multi-stage build (builder + runtime) for FastAPI + agent
│
├── data/
│   ├── raw/                      # [GITIGNORED] User-supplied CSV exports
│   │   ├── musicbuddy.csv        # MusicBuddy export (primary music source)
│   │   ├── bookbuddy.csv         # BookBuddy export (books + manga)
│   │   ├── goodreads.csv         # Goodreads export (books + manga)
│   │   ├── moviebuddy.csv        # MovieBuddy export (movies + anime)
│   │   └── letterboxd.csv        # Letterboxd export (movies)
│   ├── tmp/                      # [GITIGNORED] Temporary DuckDB during ingestion pipeline
│   │   └── warehouse.duckdb      # Written by ingestion subprocess; replaces main db on success
│   ├── templates/                # CSV templates for users without Buddy+/Goodreads/Letterboxd
│   │   ├── template_music.csv
│   │   ├── template_books.csv
│   │   ├── template_manga.csv
│   │   ├── template_movies.csv
│   │   ├── template_series.csv
│   │   └── template_anime.csv
│   └── warehouse.duckdb          # [GITIGNORED] Live DuckDB database (read by API + agent)
│
├── ingestion/                    # Python ingestion layer (CSV + API → DuckDB bronze)
│   ├── __init__.py
│   ├── base_loader.py            # Abstract base class for CSV loaders; defines load() interface
│   ├── base_api_client.py        # Abstract base class for API clients (audit columns, load())
│   ├── csv/                      # One loader per CSV source
│   │   ├── __init__.py
│   │   ├── musicbuddy_loader.py
│   │   ├── bookbuddy_loader.py
│   │   ├── goodreads_loader.py
│   │   ├── moviebuddy_loader.py
│   │   ├── letterboxd_loader.py
│   │   └── generic_loader.py     # Handles user-supplied template CSVs (any domain)
│   ├── apis/
│   │   ├── __init__.py
│   │   ├── spotify_client.py     # 30s timeout; Retry-After > 60s → skip gracefully
│   │   └── trakt_client.py       # 30s timeout; tokens expire every 90 days
│   └── run_ingestion.py          # Orchestrator: runs all loaders in dependency order
│
├── transform/                    # dbt-duckdb project (medallion architecture)
│   ├── dbt_project.yml           # dbt project config
│   ├── profiles.yml              # DuckDB connection (reads DUCKDB_PATH from env)
│   ├── models/
│   │   ├── bronze/               # Raw layer — one table per source, no transformation
│   │   │   ├── raw_musicbuddy.sql
│   │   │   ├── raw_bookbuddy.sql
│   │   │   ├── raw_goodreads.sql
│   │   │   ├── raw_moviebuddy.sql
│   │   │   ├── raw_letterboxd.sql
│   │   │   ├── raw_spotify.sql   # pre_hook creates empty table if Spotify not yet ingested
│   │   │   └── raw_trakt.sql
│   │   ├── silver/               # Staging layer — cleaned, typed, deduplicated, rated
│   │   │   ├── stg_music.sql     # MusicBuddy (primary) + Spotify (enrichment)
│   │   │   ├── stg_books.sql     # BookBuddy + Goodreads; manga detection
│   │   │   ├── stg_movies.sql    # MovieBuddy + Letterboxd + Trakt
│   │   │   ├── stg_series.sql    # Trakt shows; anime excluded
│   │   │   └── stg_anime.sql     # Anime only (known gap — DEC-019)
│   │   └── gold/                 # Mart layer — analytical models for frontend + agent
│   │       ├── mart_unified_tastes.sql   # All domains unified
│   │       ├── mart_ratings.sql          # Current rating per item (incremental — DEC-030)
│   │       ├── mart_rating_events.sql    # Append-only audit trail
│   │       ├── mart_top_rated.sql        # Top-rated items per domain
│   │       └── mart_taste_profile.sql    # Aggregate stats: genres, creators, decades
│   └── seeds/
│       ├── manga_publishers.csv          # Known manga publishers for detection
│       └── domain_mapping.csv            # Category → domain override map
│
├── agent/                        # LangGraph conversational agent
│   ├── __init__.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── sql_tool.py           # Natural language → SQL → DuckDB → formatted result
│   │   ├── rating_tool.py        # Add/update rating (search + submit, two steps)
│   │   └── recommend_tool.py     # Cross-domain recommendations based on taste profile
│   ├── graph.py                  # LangGraph graph (nodes, edges, state, memory)
│   ├── prompts.py                # System prompts in French and English
│   └── app.py                    # Chainlit entry point (sys.path fix at top — DEC-024)
│
├── api/                          # FastAPI backend (the only layer that touches DuckDB)
│   ├── __init__.py
│   ├── main.py                   # FastAPI app: CORS, lifespan, router registration
│   │                             # Lifespan skips ensure_table if warehouse.duckdb missing (DEC-036)
│   │                             # CORS reads FRONTEND_URL + TASTEBASE_AGENT_URL in production
│   ├── dependencies.py           # get_db (read_only=True) + get_db_write (read_only=False)
│   │                             # Split to avoid DuckDB write lock during ingestion (DEC-037)
│   ├── routers/
│   │   ├── items.py              # GET/POST/PATCH/DELETE taste items
│   │   ├── ratings.py            # POST rating (get_db_write), GET rating/history (get_db)
│   │   ├── categories.py         # GET/POST per-item category (get_db_write for writes)
│   │   ├── ingestion.py          # POST /ingest (writes to data/tmp/warehouse.duckdb — DEC-038)
│   │   └── stats.py              # GET endpoints for Insights charts (counts, top lists, profile)
│   └── schemas/
│       ├── item.py               # Pydantic: TasteItem, TasteItemCreate, PaginatedItems
│       ├── rating.py             # Pydantic: Rating, RatingCreate, RatingEvent
│       └── category.py           # Pydantic: CategoryUpsert, CategoryBatch, Category
│
├── frontend/                     # Vue 3 + Vite single-page application (deployed on Netlify)
│   ├── index.html
│   ├── vite.config.js            # Vue plugin, SCSS injection via import.meta.url, dev proxy → :8000
│   ├── package.json              # chart.js, vue-chartjs, vue-router, vue-i18n, axios, sass
│   ├── netlify.toml              # Netlify build config: base=frontend, publish=dist, SPA redirect
│   └── src/
│       ├── main.js               # App bootstrap: Vue, vue-router, vue-i18n
│       ├── App.vue               # Root: AppSidebar + RouterView layout
│       ├── api/                  # Thin Axios modules — one per FastAPI router
│       │   ├── client.js         # Axios instance (baseURL VITE_API_BASE_URL, timeout 30s)
│       │   ├── items.js
│       │   ├── ratings.js
│       │   ├── categories.js
│       │   ├── stats.js          # fetchCounts, fetchRecent, fetchTasteProfile, parseTasteProfile
│       │   └── ingestion.js
│       ├── config/
│       │   ├── domains.js        # Domain metadata: key, label, icon, color, route
│       │   └── categories.js     # Full genre/sub-genre taxonomy per domain
│       ├── i18n/
│       │   ├── fr.json           # French UI strings (default) — includes insights.* keys
│       │   └── en.json           # English UI strings — includes insights.* keys
│       ├── router/
│       │   └── index.js          # Routes: home, 6 domain views, /insights
│       ├── views/
│       │   ├── HomeView.vue      # Domain cards grid with item + rated counts
│       │   ├── InsightsView.vue  # KPI strip + 4 Chart.js visualisations
│       │   └── [Domain]View.vue  # Per-domain paginated browse (MusicView, BooksView, etc.)
│       └── components/
│           ├── AppSidebar.vue        # Nav: domains, Insights (internal), Agent (external)
│           ├── FilterBar.vue
│           ├── ItemCard.vue
│           ├── StarRating.vue
│           ├── CategorySelector.vue
│           ├── BatchCategoryBar.vue
│           ├── AddItemModal.vue
│           ├── UploadModal.vue
│           └── charts/               # Chart.js components (vue-chartjs wrappers)
│               ├── DomainBreakdownChart.vue   # Doughnut: items per domain
│               ├── RatingDistributionChart.vue # Bar: ratings 1–5 per domain
│               ├── DecadesChart.vue            # Stacked bar: items by decade
│               └── TopCreatorsChart.vue        # Horizontal bar: top creators (filterable)
│
├── tests/                        # pytest test suite
│   ├── ingestion/
│   │   ├── test_musicbuddy_loader.py
│   │   ├── test_bookbuddy_loader.py
│   │   ├── test_goodreads_loader.py
│   │   ├── test_moviebuddy_loader.py
│   │   ├── test_letterboxd_loader.py
│   │   ├── test_spotify_client.py    # Mocked HTTP responses
│   │   └── test_trakt_client.py      # Mocked HTTP responses
│   └── api/
│       ├── test_items.py
│       ├── test_ratings.py
│       └── test_stats.py
│
└── docs/
    ├── data-sources.md           # Export instructions per app + Trakt OAuth refresh guide
    ├── csv-templates.md          # Column reference for each custom template
    ├── deployment.md             # Coolify + Hetzner VPS setup guide
    └── contributing.md           # How to contribute
```

---

## Layer responsibilities

| Layer  | Prefix  | Materialization     | Responsibility                                   |
| ------ | ------- | ------------------- | ------------------------------------------------ |
| Bronze | `raw_`  | table               | Raw data as-is; never modified after ingestion   |
| Silver | `stg_`  | view                | Clean, typed, domain-tagged, deduplicated, rated |
| Gold   | `mart_` | table / incremental | Analytical marts for frontend widgets and agent  |

## Satellite tables (outside dbt DAG)

These tables live in `main_gold` but are managed by FastAPI — `dbt run` never touches them.

| Table                  | Created by          | Purpose                                              |
| ---------------------- | ------------------- | ---------------------------------------------------- |
| `mart_ratings`         | dbt (incremental)   | Current rating per item — user ratings preserved     |
| `mart_rating_events`   | dbt (table)         | Append-only rating audit trail                       |
| `mart_item_categories` | FastAPI lifespan    | User-assigned genre/sub_genre per item               |

## Ingestion isolation pattern

```
POST /ingest/upload
    → save CSV to data/raw/<canonical>.csv
    → subprocess: run_ingestion.py (DUCKDB_PATH=data/tmp/warehouse.duckdb)
    → subprocess: dbt run         (DUCKDB_PATH=data/tmp/warehouse.duckdb)
    → on success: shutil.move(tmp → data/warehouse.duckdb)
    → API's read-only connections to warehouse.duckdb are never blocked
```

See DEC-037, DEC-038, DEC-039.
