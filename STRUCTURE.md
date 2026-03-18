# STRUCTURE.md — TasteBase

> Annotated folder/file structure. Updated as new files are added.
> Each entry explains **what the file is** and **why it exists**.

---

```
tastebase/
│
├── .env.example                  # Environment variable template (never commit .env)
├── .gitignore                    # Ignores data/raw/, .env, __pycache__, .dbt/, etc.
├── CONTEXT.md                    # Source of truth: architecture, stack, design decisions
├── DECISIONS.md                  # Log of architectural and technical decisions with rationale
├── NEXT_STEPS.md                 # Ordered roadmap; checked items = done, unchecked = todo
├── STRUCTURE.md                  # This file — annotated project structure
├── README.md                     # Public-facing project overview and quickstart
├── Makefile                      # Developer commands (install, ingest, transform, etc.)
├── docker-compose.yml            # Defines api, agent, and dashboard services
├── Dockerfile                    # Multi-stage build for the FastAPI + ingestion service
├── requirements.txt              # Python dependencies (pinned versions)
│
├── data/
│   ├── raw/                      # [GITIGNORED] User-supplied CSV exports
│   │   ├── musicbuddy.csv        # MusicBuddy export (primary music source)
│   │   ├── bookbuddy.csv         # BookBuddy export (books + manga)
│   │   ├── goodreads.csv         # Goodreads export (books + manga)
│   │   ├── moviebuddy.csv        # MovieBuddy export (movies + anime)
│   │   └── letterboxd.csv        # Letterboxd export (movies)
│   ├── templates/                # CSV templates for users without Buddy+/Goodreads/Letterboxd
│   │   ├── template_music.csv    # Standard columns for music entries
│   │   ├── template_books.csv    # Standard columns for book entries
│   │   ├── template_manga.csv    # Standard columns for manga entries
│   │   ├── template_movies.csv   # Standard columns for movie entries
│   │   ├── template_series.csv   # Standard columns for series entries
│   │   └── template_anime.csv    # Standard columns for anime entries
│   └── warehouse.duckdb          # [GITIGNORED] Generated DuckDB database file
│
├── ingestion/                    # Python ingestion layer (CSV + API → DuckDB bronze)
│   ├── __init__.py
│   ├── base_loader.py            # Abstract base class for CSV loaders; defines load() interface
│   ├── base_api_client.py        # Abstract base class for API clients (separate from BaseLoader)
│   ├── csv/                      # One loader per CSV source
│   │   ├── __init__.py
│   │   ├── musicbuddy_loader.py  # Parses musicbuddy.csv → raw_musicbuddy table
│   │   ├── bookbuddy_loader.py   # Parses bookbuddy.csv → raw_bookbuddy table
│   │   ├── goodreads_loader.py   # Parses goodreads.csv → raw_goodreads table
│   │   ├── moviebuddy_loader.py  # Parses moviebuddy.csv → raw_moviebuddy table
│   │   ├── letterboxd_loader.py  # Parses letterboxd.csv → raw_letterboxd table
│   │   └── generic_loader.py     # Handles user-supplied template CSVs (any domain)
│   ├── apis/                     # One client per external API
│   │   ├── __init__.py
│   │   ├── spotify_client.py     # Fetches saved albums, recently played, top items (30s timeout; Retry-After capped at 60s)
│   │   └── trakt_client.py       # Fetches watched movies, watched shows, ratings (30s timeout)
│   └── run_ingestion.py          # Orchestrator: runs all loaders in dependency order
│
├── transform/                    # dbt-duckdb project (medallion architecture)
│   ├── dbt_project.yml           # dbt project config (name, version, model paths)
│   ├── profiles.yml              # DuckDB connection profile (reads DUCKDB_PATH from env)
│   ├── models/
│   │   ├── bronze/               # Raw layer — one table per source, no transformation
│   │   │   ├── raw_musicbuddy.sql    # Materializes raw_musicbuddy as table
│   │   │   ├── raw_bookbuddy.sql     # Materializes raw_bookbuddy as table
│   │   │   ├── raw_goodreads.sql     # Materializes raw_goodreads as table
│   │   │   ├── raw_moviebuddy.sql    # Materializes raw_moviebuddy as table
│   │   │   ├── raw_letterboxd.sql    # Materializes raw_letterboxd as table
│   │   │   ├── raw_spotify.sql       # Materializes raw_spotify as table (pre_hook creates empty table if missing)
│   │   │   └── raw_trakt.sql         # Materializes raw_trakt as table
│   │   ├── silver/               # Staging layer — cleaned, typed, deduplicated, rated
│   │   │   ├── stg_music.sql         # MusicBuddy (primary) + Spotify (enrichment)
│   │   │   ├── stg_books.sql         # BookBuddy + Goodreads; includes manga detection
│   │   │   ├── stg_movies.sql        # MovieBuddy + Letterboxd + Trakt; includes anime detection
│   │   │   ├── stg_series.sql        # Trakt shows only; anime excluded
│   │   │   └── stg_anime.sql         # MovieBuddy (TV Show + Anime genre) + Trakt anime
│   │   └── gold/                 # Mart layer — analytical models for dashboard + agent
│   │       ├── mart_unified_tastes.sql   # All domains unified into a single model
│   │       ├── mart_ratings.sql          # Current rating per item — incremental to preserve user ratings
│   │       ├── mart_rating_events.sql    # Append-only audit trail of rating changes
│   │       ├── mart_top_rated.sql        # Top-rated items per domain (filterable)
│   │       └── mart_taste_profile.sql    # Aggregate stats: genres, creators, decades
│   └── seeds/
│       ├── manga_publishers.csv      # Known manga publishers (Viz, Kodansha, etc.)
│       └── domain_mapping.csv        # Category → domain override (e.g. "BD" → manga)
│
├── agent/                        # LangGraph conversational agent
│   ├── __init__.py
│   ├── tools/                    # Individual LangGraph tools (called by the agent)
│   │   ├── __init__.py
│   │   ├── sql_tool.py           # Natural language → SQL → DuckDB → formatted result
│   │   ├── rating_tool.py        # Add or update a rating via the FastAPI endpoint
│   │   └── recommend_tool.py     # Cross-domain recommendations based on taste profile
│   ├── graph.py                  # LangGraph graph definition (nodes, edges, state)
│   ├── prompts.py                # System prompts in French and English
│   └── app.py                    # Chainlit app entry point (mounts the LangGraph agent)
│
├── api/                          # FastAPI backend (the only layer that touches DuckDB)
│   ├── __init__.py
│   ├── main.py                   # FastAPI app: CORS, lifespan, router registration
│   ├── dependencies.py           # get_db: per-request DuckDB connection via Depends
│   ├── routers/
│   │   ├── items.py              # GET/POST/PATCH/DELETE taste items
│   │   ├── ratings.py            # POST rating → inserts into mart_ratings + rating_events
│   │   ├── categories.py         # GET/POST per-item category, POST /categories/batch
│   │   ├── ingestion.py          # POST /ingest (pipeline trigger), POST /ingest/upload (CSV upload), GET /ingest/sources
│   │   └── stats.py              # GET endpoints for dashboard widgets (counts, top lists)
│   └── schemas/
│       ├── item.py               # Pydantic models: TasteItem, TasteItemCreate, etc.
│       ├── rating.py             # Pydantic models: Rating, RatingCreate, RatingEvent
│       └── category.py           # Pydantic models: CategoryUpsert, CategoryBatch, Category
│
├── frontend/                     # Vue 3 + Vite single-page application
│   ├── index.html                # SPA entry point
│   ├── vite.config.js            # Vite config: Vue plugin, SCSS injection, dev proxy → :8000
│   ├── package.json
│   └── src/
│       ├── main.js               # App bootstrap: Vue, vue-router, vue-i18n
│       ├── App.vue               # Root component: AppSidebar + RouterView layout
│       ├── api/                  # Thin Axios modules — one per FastAPI router
│       │   ├── client.js         # Axios instance (baseURL /api, timeout 30s, error normalization)
│       │   ├── items.js          # fetchItems, fetchItem, createItem, deleteItem
│       │   ├── ratings.js        # fetchRating, upsertRating
│       │   ├── categories.js     # fetchCategory, upsertCategory, batchUpsertCategories
│       │   ├── stats.js          # fetchCounts, fetchRecent, fetchTasteProfile
│       │   └── ingestion.js      # fetchSources, uploadCsv (timeout=0 for long pipeline runs)
│       ├── config/
│       │   ├── domains.js        # Domain metadata: key, label, icon, color, route
│       │   └── categories.js     # Full genre/sub-genre taxonomy per domain
│       ├── i18n/
│       │   ├── fr.json           # French UI strings (default language)
│       │   └── en.json           # English UI strings
│       ├── router/
│       │   └── index.js          # Vue Router: one route per domain + home
│       ├── views/
│       │   ├── HomeView.vue      # Domain cards grid with item + rated counts
│       │   └── ItemBrowser.vue   # Paginated browse grid with FilterBar
│       └── components/
│           ├── AppSidebar.vue        # Domain nav, language toggle, Import CSV button, collapse
│           ├── FilterBar.vue         # Search, rating chips, decade chips, genre selects, sort
│           ├── ItemCard.vue          # Title, creator, year, star rating, category badge
│           ├── StarRating.vue        # Read-only + interactive star widget
│           ├── CategorySelector.vue  # Chained genre/sub-genre selects per domain
│           ├── BatchCategoryBar.vue  # Multi-select batch category assignment
│           ├── AddItemModal.vue      # Manual item creation form
│           └── UploadModal.vue       # CSV drag-and-drop upload: source select, progress, pipeline logs
│
├── dashboard/                    # Evidence.dev static dashboard
│   ├── sources/
│   │   └── tastebase/
│   │       ├── connection.yaml       # DuckDB connection config (read_only: true)
│   │       └── warehouse.duckdb      # [GITIGNORED] Physical copy of data/warehouse.duckdb
│   └── pages/
│       ├── index.md              # Overview: counts per domain, recently added
│       ├── music.md              # Music: top albums, genres, artists
│       ├── books.md              # Books: top rated, authors, languages
│       ├── manga.md              # Manga: top rated, publishers, volumes
│       ├── movies.md             # Movies: top rated, directors, decades
│       ├── series.md             # Series: top rated, networks, genres
│       └── anime.md              # Anime: top rated, studios, seasons (guarded — DEC-019)
│
├── tests/                        # pytest test suite
│   ├── ingestion/
│   │   ├── test_musicbuddy_loader.py
│   │   ├── test_bookbuddy_loader.py
│   │   ├── test_goodreads_loader.py
│   │   ├── test_moviebuddy_loader.py
│   │   ├── test_letterboxd_loader.py
│   │   ├── test_spotify_client.py    # Uses mocked HTTP responses
│   │   └── test_trakt_client.py      # Uses mocked HTTP responses
│   └── api/
│       ├── test_items.py
│       ├── test_ratings.py
│       └── test_stats.py
│
└── docs/
    ├── data-sources.md           # Step-by-step export instructions per app
    ├── csv-templates.md          # Column reference for each custom template
    ├── deployment.md             # Coolify + Hetzner VPS setup guide
    └── contributing.md           # How to contribute (fork, branch, PR conventions)
```

---

## Layer responsibilities

| Layer  | Prefix  | Materialization | Responsibility                                   |
| ------ | ------- | --------------- | ------------------------------------------------ |
| Bronze | `raw_`  | table           | Raw data as-is; never modified after ingestion   |
| Silver | `stg_`  | view            | Clean, typed, domain-tagged, deduplicated, rated |
| Gold   | `mart_` | table / incremental | Analytical marts for dashboard widgets and agent |

## Key data flow

```
CSV files / APIs
    → ingestion/ (Python loaders)
    → DuckDB bronze (raw_ tables)
    → dbt silver (stg_ views)
    → dbt gold (mart_ tables)
    → FastAPI (api/)          ← frontend reads/writes here
    → LangGraph agent (agent/) ← queries gold only
    → Evidence.dev dashboard  ← reads gold directly via DuckDB
```

## Satellite tables (outside dbt DAG)

These tables live in `main_gold` but are managed entirely by FastAPI — `dbt run` never
touches them. They survive all pipeline rebuilds.

| Table                  | Created by          | Purpose                              |
| ---------------------- | ------------------- | ------------------------------------ |
| `mart_ratings`         | dbt (incremental)   | Current rating per item — user ratings preserved across runs |
| `mart_rating_events`   | dbt (table)         | Append-only rating audit trail       |
| `mart_item_categories` | FastAPI lifespan    | User-assigned genre/sub_genre per item |
