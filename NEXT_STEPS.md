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
- [x] Create `requirements.txt` with pinned dependencies
- [x] Create `docker-compose.yml` skeleton
- [x] Create `Dockerfile` skeleton

**Branch:** `feat/repo-skeleton`

---

## Phase 2 — CSV ingestion (bronze layer)

- [x] Implement `base_loader.py`
- [x] Implement all CSV loaders (musicbuddy, bookbuddy, goodreads, moviebuddy, letterboxd, generic)
- [x] Implement `run_ingestion.py` orchestrator
- [x] Write bronze dbt models (`raw_` prefix, materialized as `table`)
- [x] Write pytest tests for all loaders

**Branch:** `feat/csv-ingestion-bronze`

---

## Phase 3 — API ingestion (bronze layer)

- [x] Implement `spotify_client.py` and `trakt_client.py`
- [x] Extend `run_ingestion.py` for API sources
- [x] Write bronze dbt models for Spotify and Trakt
- [x] Write pytest tests for API clients (mocked responses)

**Branch:** `feat/api-ingestion-bronze`

---

## Phase 4 — Silver layer (normalization + deduplication)

- [x] Add dbt seeds: `manga_publishers.csv`, `domain_mapping.csv`
- [x] Write all silver models (`stg_music`, `stg_books`, `stg_movies`, `stg_series`, `stg_anime`)
- [x] Implement deduplication logic (canonical ID → rating priority → date)
- [x] Normalize all ratings to 1–5 integer scale

**Known issues / backlog:**
- `stg_anime` returns 0 rows: MovieBuddy exports "Animation" not "Anime" (TMDB). Fix via country enrichment or curated seed.
- `stg_series` contains anime titles until detection signal is improved.

**Branch:** `feat/silver-layer`

---

## Phase 4b — Silver schema tests

- [x] Write dbt schema tests for all silver models (62/62 PASS)

**Branch:** `feat/silver-schema-tests`

---

## Phase 5 — Gold layer (analytical marts)

- [x] Write all gold models (`mart_unified_tastes`, `mart_ratings`, `mart_rating_events`, `mart_top_rated`, `mart_taste_profile`)
- [x] Write dbt schema tests for gold models (31/31 passing)

**Branch:** `feat/gold-layer`

---

## Phase 6 — FastAPI backend

- [x] Implement `api/dependencies.py` (`get_db` / `get_db_write` per-request connections)
- [x] Implement `api/main.py` (FastAPI app, CORS, lifespan, `/health`)
- [x] Implement all routers (`items`, `ratings`, `ingestion`, `stats`, `categories`)
- [x] Define Pydantic schemas
- [x] Write pytest tests (~20 tests, in-memory DuckDB fixtures)

**Branch:** `feat/fastapi-backend`

---

## Phase 7 — CSV templates

- [x] Create all 6 domain templates in `data/templates/`
- [x] Write `docs/csv-templates.md`

**Branch:** `feat/csv-templates`

---

## Phase 8 — LangGraph agent

- [x] Implement `sql_tool.py`, `rating_tool.py`, `recommend_tool.py`
- [x] Implement `graph.py` (LangGraph agent with state, tools, memory)
- [x] Write `prompts.py` (FR and EN)
- [x] Implement `agent/app.py` (Chainlit entry point)

**Branch:** `feat/langgraph-agent`

---

## Phase 9 — Evidence.dev dashboard (superseded)

- [x] Evidence.dev dashboard implemented and deployed
- **Superseded by Phase 15** — Evidence.dev removed, replaced by Vue 3 Insights pages

**Branch:** `feat/evidence-dashboard`

---

## Phase 10 — Frontend UI

- [x] Scaffold Vite + Vue 3 + Vue Router + vue-i18n + Axios
- [x] SCSS design system
- [x] All views and components (HomeView, ItemBrowser, FilterBar, ItemCard, etc.)
- [x] All API modules (`api/items.js`, `api/ratings.js`, `api/categories.js`, `api/stats.js`, `api/ingestion.js`)
- [x] i18n: FR + EN
- [x] FastAPI extensions: categories router, hard delete, extended filters
- [x] CSV upload from the UI

**Branch:** `feat/frontend-ui`

---

## Phase 11 — Docker + deployment

- [x] Finalize `Dockerfile` (multi-stage, Python 3.12, healthcheck)
- [x] Finalize `docker-compose.yml`
- [x] Write `docs/deployment.md`
- [x] Configure DuckDB volume persistence
- [x] Create `.dockerignore`

**Branch:** `feat/docker-deployment`

---

## Phase 12 — Documentation + open source

- [x] Write `README.md`
- [x] Write `docs/data-sources.md`, `docs/contributing.md`
- [x] Make repository public on GitHub

**Branch:** `feat/documentation`

---

## Phase 13 — Agent bugfixes & UX polish

- [x] Fix deprecated model → `claude-haiku-4-5-20251001`
- [x] Fix DuckDB `search_path` missing in `sql_tool._execute_sql`
- [x] Fix Chainlit streaming (suppress pre-tool tokens, normalize `AIMessage.content`)
- [x] Fix `recommend_tool` JSON parsing and pagination
- [x] Add `load_dotenv()` to `api/main.py` and `agent/app.py`
- [x] Add collection exclusion list to recommendation prompt

**Branch:** `fix/agent-bugfixes`

---

## Phase 14 — Cross-app navigation & developer UX

- [x] Cross-app links in Chainlit, Vue sidebar, Evidence index
- [x] `TASTEBASE_*` env vars, `VITE_*` env vars
- [x] Personalize `chainlit.md`
- [x] Update Makefile (`make frontend`, `make stack`, `make dev-all`)

**Branch:** `feat/cross-app-navigation-links`

---

## Phase 15 — Re-deployment: split architecture + Insights page

- [x] Remove Evidence.dev (`Dockerfile.dashboard`, `dashboard/` excluded from Docker)
- [x] Add Vue 3 Insights page with Chart.js (DomainBreakdown, RatingDistribution, Decades, TopCreators)
- [x] Replace external Dashboard link in sidebar with internal `/insights` route
- [x] Add `chart.js` + `vue-chartjs` to `frontend/package.json`
- [x] Split Coolify into two independent apps:
  - `tastebase-api` → `docker-compose.api.yml`
  - `tastebase-agent` → `docker-compose.agent.yml`
- [x] Add `args: {}` to build blocks to prevent Coolify `--build-arg` injection
- [x] Deploy Vue 3 frontend on Netlify (`frontend/netlify.toml`)
- [x] Fix CORS in production: read `FRONTEND_URL` + `TASTEBASE_AGENT_URL` from env
- [x] Fix `get_db()` → `read_only=True`; add `get_db_write()` for write endpoints
- [x] Fix API lifespan: skip `ensure_table` when `warehouse.duckdb` does not exist
- [x] Fix ingestion pipeline: write to `data/tmp/warehouse.duckdb` to avoid DuckDB write lock
- [x] Fix dbt catalog mismatch: use `data/tmp/warehouse.duckdb` (same stem) not `warehouse.duckdb.tmp`
- [x] Refresh Trakt OAuth tokens (90-day expiry)

**Branches:** `feat/insights-vue-charts`, `feat/split-coolify-apps-remove-evidence`,
`fix/deploy-bugs`

---

## Backlog / future improvements

- [ ] Fix duplicate items in pipeline (same movie from MovieBuddy + Letterboxd — improve silver deduplication)
- [ ] Anime detection improvement: enrich with production country (JP) or known anime titles seed (DEC-019)
- [ ] Spotify ingestion: retry after 24h rate limit window (currently skipped gracefully)
- [ ] MyAnimeList API integration
- [ ] OpenLibrary / Google Books cover enrichment
- [ ] `recommend_tool` exclusion list: LLM sometimes ignores very famous items in collection
- [ ] `recommend_tool._fetch_collection_items` pagination: only fetches first 200 items
- [ ] Background task queue for ingestion (ARQ or Celery) — ingestion currently blocks the API worker
- [ ] Multi-user support (separate DuckDB per user, or schema-per-user)
- [ ] Export taste profile as JSON/CSV
- [ ] Public taste profile page (read-only shareable URL)
- [ ] Recommendation engine using embeddings (sentence-transformers)
