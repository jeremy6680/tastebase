# NEXT_STEPS.md — TasteBase

> Roadmap ordered by dependency. Check off items as they are completed.
> Each step = one Git branch. Format: `feat/scope-description`

---

## Phase 0 — Project bootstrap

- [x] Write `CONTEXT.md` (architecture, stack, design decisions)
- [x] Write `NEXT_STEPS.md` (this file)
- [x] Write `STRUCTURE.md` (folder/file structure with explanations)
- [x] Write `DECISIONS.md` (architectural decisions log)
- [x] Write `.gitignore`

**Branch:** `feat/project-bootstrap`

---

## Phase 1 — Repository skeleton

- [x] Create all folders and empty `__init__.py` files
- [x] Create `Makefile` with all developer commands
- [x] Create `.env.example` with all required variables
- [x] Create `requirements.txt` (or `pyproject.toml`) with pinned dependencies
- [x] Create `docker-compose.yml` skeleton
- [x] Create `Dockerfile` skeleton

**Branch:** `feat/repo-skeleton`

---

## Phase 2 — CSV ingestion (bronze layer)

- [x] Implement `base_loader.py` (abstract base class for all loaders)
- [x] Implement `musicbuddy_loader.py`
- [x] Implement `bookbuddy_loader.py`
- [x] Implement `goodreads_loader.py`
- [x] Implement `moviebuddy_loader.py`
- [x] Implement `letterboxd_loader.py`
- [x] Implement `generic_loader.py` (handles user CSV templates)
- [x] Implement `run_ingestion.py` (orchestrator)
- [x] Write bronze dbt models (`raw_` prefix, materialized as `table`)
- [x] Write pytest tests for all loaders

**Branch:** `feat/csv-ingestion-bronze`

---

## Phase 3 — API ingestion (bronze layer)

- [x] Implement `spotify_client.py` (saved albums, recently played, top artists/tracks)
- [x] Implement `trakt_client.py` (watched movies, watched shows, ratings)
- [x] Extend `run_ingestion.py` to include API sources
- [x] Write bronze dbt models for Spotify and Trakt (`raw_spotify`, `raw_trakt`)
- [x] Write pytest tests for API clients (with mocked responses)

**Branch:** `feat/api-ingestion-bronze`

---

## Phase 4 — Silver layer (normalization + deduplication)

- [x] Add dbt seeds: `manga_publishers.csv`, `domain_mapping.csv`
- [x] Write `stg_music.sql` (MusicBuddy primary, Spotify enrichment via LEFT JOIN)
- [x] Write `stg_books.sql` (BookBuddy + Goodreads, manga detection via publisher + keywords)
- [x] Write `stg_movies.sql` (MovieBuddy + Letterboxd + Trakt, deduplication via IMDB ID)
- [x] Write `stg_series.sql` (MovieBuddy TV Show + Trakt shows, anime excluded)
- [x] Write `stg_anime.sql` (MovieBuddy TV Show + Trakt, anime only — see known issue)
- [x] Implement deduplication logic (canonical ID → rating priority → date)
- [x] Normalize all ratings to 1–5 integer scale

**Known issues / backlog from Phase 4:**

- `stg_anime` returns 0 rows: MovieBuddy exports genre as "Animation" (TMDB), not "Anime".
  Fix: enrich with production country (JP) or maintain a known anime titles seed.
- `stg_series` contains anime titles (Bakuman, Death Note, Kuroko's Basketball, etc.)
  until the anime detection signal is improved.
- Spotify enrichment in `stg_music` returns 0 matches (rate-limited during dev).
  Will resolve automatically when `make ingest` runs post rate-limit.
- `raw_spotify.sql` uses a `pre_hook` to create `main.raw_spotify` if missing,
  avoiding a circular dependency when Spotify hasn't been ingested yet.
- `run_ingestion.py` had a kwarg mismatch (`csv_path` vs `file_path`) — fixed.
- `raw_moviebuddy.sql` had a reserved word issue (`cast`) — fixed with quoting.
- `dbt_project.yml` schema prefixes require `DUCKDB_PATH` to be an absolute path
  in `.env` (relative paths are resolved from `transform/`, not the project root).

**Branch:** `feat/silver-layer`

---

## Phase 4b — Silver schema tests

- [x] Write dbt schema tests for all silver models (`stg_music`, `stg_books`, `stg_movies`, `stg_series`, `stg_anime`)

**Result:** 62/62 PASS, 0 WARN, 0 ERROR

**Branch:** `feat/silver-schema-tests`

---

## Phase 5 — Gold layer (analytical marts)

- [x] Write `mart_unified_tastes.sql` (full unified view across all domains)
- [x] Write `mart_ratings.sql` (current rating per item, source-tracked)
- [x] Write `mart_rating_events.sql` (append-only audit trail, bootstrapped from imports)
- [x] Write `mart_top_rated.sql` (top items per domain, filterable)
- [x] Write `mart_taste_profile.sql` (aggregate stats: genres, creators, decades)
- [x] Write dbt schema tests for gold models (31/31 passing)

**Branch:** `feat/gold-layer`

---

## Phase 6 — FastAPI backend

- [x] Implement `api/dependencies.py` (`get_db`: per-request DuckDB connection via contextmanager)
- [x] Implement `api/main.py` (FastAPI app, CORS, lifespan, `/health`)
- [x] Implement `routers/items.py` (CRUD for taste items: GET list, GET single, POST, PATCH)
- [x] Implement `routers/ratings.py` (upsert rating, get rating, rating history)
- [x] Implement `routers/ingestion.py` (trigger re-ingestion via subprocess)
- [x] Implement `routers/stats.py` (counts, top-rated, taste profile, recent)
- [x] Define Pydantic schemas in `schemas/item.py` and `schemas/rating.py`
- [x] Write pytest tests for all endpoints (in-memory DuckDB fixtures, ~20 tests)

**Branch:** `feat/fastapi-backend`

---

## Phase 7 — CSV templates

- [x] Create `data/templates/template_music.csv`
- [x] Create `data/templates/template_books.csv`
- [x] Create `data/templates/template_manga.csv`
- [x] Create `data/templates/template_movies.csv`
- [x] Create `data/templates/template_series.csv`
- [x] Create `data/templates/template_anime.csv`
- [x] Write `docs/csv-templates.md` (documentation for each template)

**Branch:** `feat/csv-templates`

---

## Phase 8 — LangGraph agent

- [x] Implement `sql_tool.py` (natural language → DuckDB SQL via LLM)
- [x] Implement `rating_tool.py` (add/update rating via FastAPI)
- [x] Implement `recommend_tool.py` (cross-domain recommendations)
- [x] Implement `graph.py` (LangGraph agent with state, tools, memory)
- [x] Write `prompts.py` (system prompts in FR and EN)
- [x] Implement `agent/app.py` (Chainlit entry point)

**Branch:** `feat/langgraph-agent`

---

## Phase 9 — Evidence.dev dashboard

- [x] Initialize Evidence.dev project in `dashboard/` (`npx degit evidence-dev/template . --force`)
- [x] Configure DuckDB connection (`sources/tastebase/connection.yaml`, `read_only: true`)
- [x] Add source queries for gold layer (`unified_tastes.sql`, `ratings.sql`, `top_rated.sql`, `taste_profile.sql`)
- [x] Add `make dashboard-sync` and `make dashboard` commands to Makefile
- [x] Create page: overview (`index.md`) — domain counts, top genres, top creators, decades, recently added
- [x] Create page: music (`music.md`) — BigValues, top rated, all albums, top artists
- [x] Create page: books (`books.md`) — BigValues, top rated, top authors
- [x] Create page: manga (`manga.md`) — BigValues, top rated, top authors
- [x] Create page: movies (`movies.md`) — BigValues, top rated, top directors, by decade
- [x] Create page: series (`series.md`) — BigValues, top rated (guarded), all series, by decade
- [x] Create page: anime (`anime.md`) — guarded display pending DEC-019 fix

**Known issues carried forward:**

- Music and series have 0 rated items → top rated sections display a Note component instead of empty tables
- Anime has 0 items → all sections guarded with `{#if}` (DEC-019)
- `warehouse.duckdb` must be manually synced via `make dashboard-sync` before each Evidence session

**Branch:** `feat/evidence-dashboard`

---

## Phase 10 — Frontend UI

- [x] Scaffold Vite + Vue 3 + Vue Router + vue-i18n + Axios (DEC-028)
- [x] SCSS design system: variables, reset, layout utilities
- [x] `AppSidebar`: domain navigation, collapse state, FR/EN language toggle
- [x] `HomeView`: domain cards grid with counts from `/stats/counts`
- [x] `ItemBrowser`: paginated grid, filter state, domain-aware
- [x] `FilterBar`: search (title + creator), rating chips, decade chips, genre/sub-genre selects, sort
- [x] `ItemCard`: title, creator, year, interactive star rating, category badge
- [x] `StarRating`: read-only + interactive mode, hover preview, saving spinner
- [x] `CategorySelector`: chained genre/sub-genre selects per domain
- [x] `BatchCategoryBar`: Cmd/Ctrl+click multi-select, batch category apply
- [x] `AddItemModal`: manual item creation (title, creator, year, rating, status, category)
- [x] `api/items.js`: fetchItems, fetchItem, createItem, deleteItem
- [x] `api/ratings.js`: fetchRating, upsertRating
- [x] `api/categories.js`: fetchCategory, upsertCategory, batchUpsertCategories
- [x] `config/categories.js`: full genre/sub-genre taxonomy (book, music, movie, series, anime, manga)
- [x] Item deletion: button on hover, confirmation dialog, optimistic card removal
- [x] i18n: FR (default) + EN, all UI strings covered
- [x] FastAPI extensions for Phase 10 features:
  - `routers/categories.py` (GET/POST per-item, POST /categories/batch)
  - `schemas/category.py` (CategoryUpsert, CategoryBatch, Category)
  - `DELETE /items/{item_id}` (hard delete with satellite table cleanup)
  - `GET /items` extended: genre/sub_genre filter, search by creator, sort params
  - `POST /items` fixed: genres as VARCHAR, removed non-existent columns
  - `get_db` search_path fixed to resolve `main_gold,main_silver,main_bronze,main`
- [x] Upload CSV — trigger ingestion from the UI

**Known issues / notes:**

- Delete is a hard delete — dbt-managed items reappear on next `dbt run` (by design)
- Genre filter uses INNER JOIN on `mart_item_categories` — only categorised items appear
- Upload runs the full pipeline synchronously; other API requests are blocked during ingestion. Run uvicorn with `--workers 4` to mitigate. Background task queue is a Phase 11+ improvement.
- Spotify is rate-limited (~23h window); ingestion skips Spotify gracefully with a WARNING log

**Branch:** `feat/frontend-ui`

---

## Phase 11 — Docker + deployment

- [x] Finalize `Dockerfile` (multi-stage build, Python 3.12, healthcheck)
- [x] Create `Dockerfile.dashboard` (Node 20, Evidence.dev)
- [x] Finalize `docker-compose.yml` (api, agent, dashboard — healthcheck, volumes, internal network)
- [x] Write `docs/deployment.md` (Coolify + Hetzner setup guide)
- [x] Configure DuckDB volume persistence
- [x] Create `.dockerignore`
- [x] Fix `.gitignore` (remove erroneous `*.dockerignore` exclusion)

**Branch:** `feat/docker-deployment`

---

## Phase 12 — Documentation + open source

- [x] Write `README.md` (project overview, quickstart, architecture diagram)
- [x] Write `docs/data-sources.md` (export instructions per app)
- [x] Write `docs/contributing.md`
- [x] Make repository public on GitHub

**Branch:** `feat/documentation`

---

## Phase 13 — Agent bugfixes & UX polish

- [x] Fix model `claude-3-5-haiku-20241022` → `claude-haiku-4-5-20251001` (model deprecated)
- [x] Fix DuckDB `search_path` missing in `sql_tool._execute_sql` (tables not found without schema prefix)
- [x] Add `SELECT DISTINCT` instruction to SQL generation prompt (duplicate rows)
- [x] Fix `app.py` streaming: suppress pre-tool tokens, display only final reformulated answer
- [x] Fix `t.trim is not a function`: `AIMessage.content` can be a list of blocks — normalize via `_extract_text()`
- [x] Fix `recommend_tool`: `details` field from DuckDB `json_object()` is a JSON string — parse with `json.loads()`
- [x] Add `load_dotenv()` to `api/main.py` and `agent/app.py` — env vars now loaded automatically at startup
- [x] Fix `recommend_tool._fetch_collection_items`: `/items` returns `PaginatedItems` dict, not a list — extract `data["items"]`
- [x] Fix `recommend_tool._fetch_collection_items`: `/items/` 307 redirect — use trailing slash in URL
- [x] Add collection exclusion list to recommendation prompt (items already owned are listed as DO NOT RECOMMEND)

**Known remaining issues:**
- `AGENT_MODEL` env var now controls the model for all three `_get_llm()` calls (graph, sql_tool, recommend_tool)
- Recommendation exclusion list partially works — LLM sometimes ignores it for very famous items
- `/items?limit=200` covers collections up to 200 items per page; larger collections need pagination

**Branch:** `fix/agent-bugfixes`

---

## Phase 14 — Cross-app navigation & developer UX

- [x] Add quick access links in Chainlit welcome message (dashboard + library) via `TASTEBASE_*` env vars
- [x] Add external links to dashboard and agent in Vue sidebar footer via `VITE_*` env vars
- [x] Add cross-app links in Evidence index page via `PUBLIC_*` env vars (SvelteKit)
- [x] Add `frontend/.env.example`, `dashboard/.env.example` with URL variables
- [x] Update `.env.example` with `TASTEBASE_DASHBOARD_URL`, `TASTEBASE_LIBRARY_URL`, `TASTEBASE_AGENT_URL`
- [x] Personalize `chainlit.md` (replace default Chainlit placeholder)
- [x] Add `make frontend`, `make stack`, `make dev-all` to Makefile
- [x] Update `make help` with new targets
- [x] Update `README.md` — simplify Running locally section, lead with `make dev-all`
- [x] Update `CONTEXT.md` — document all Makefile commands with ports

**Branch:** `feat/cross-app-navigation-links`

---

## Backlog / future improvements

- [ ] Fix duplicate items in pipeline (e.g. same movie from MovieBuddy + Letterboxd with different metadata — improve silver deduplication)
- [ ] Book categories: `genre`/`sub_genre` filter in browse is already in place; consider auto-detection from Goodreads shelves
- [ ] MyAnimeList API integration
- [ ] OpenLibrary / Google Books cover enrichment
- [ ] Smoke test Spotify `_fetch_saved_albums` (token rate-limited during Phase 3 — retest when limit lifts)
- [ ] Spotify cover art enrichment for albums (Spotify enrichment in stg_music is ready, awaiting data)
- [ ] Anime detection improvement: enrich with production country (JP) or maintain a known anime titles seed to fix stg_anime 0-row issue
- [ ] Multi-user support (separate DuckDB per user, or schema-per-user)
- [ ] Export taste profile as JSON/CSV
- [ ] Recommendation engine using embeddings (sentence-transformers)
- [ ] `recommend_tool` exclusion list: LLM ignores very famous items already in collection — consider SQL-level pre-filtering of artists already present before LLM call
- [ ] `recommend_tool._fetch_collection_items` pagination: only fetches first 200 items — add loop for larger collections
- [ ] Public taste profile page (read-only shareable URL)
