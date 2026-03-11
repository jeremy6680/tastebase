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

- [ ] Implement `base_loader.py` (abstract base class for all loaders)
- [ ] Implement `musicbuddy_loader.py`
- [ ] Implement `bookbuddy_loader.py`
- [ ] Implement `goodreads_loader.py`
- [ ] Implement `moviebuddy_loader.py`
- [ ] Implement `letterboxd_loader.py`
- [ ] Implement `generic_loader.py` (handles user CSV templates)
- [ ] Implement `run_ingestion.py` (orchestrator)
- [ ] Write bronze dbt models (`raw_` prefix, materialized as `table`)
- [ ] Write pytest tests for all loaders

**Branch:** `feat/csv-ingestion-bronze`

---

## Phase 3 — API ingestion (bronze layer)

- [ ] Implement `spotify_client.py` (saved albums, recently played, top artists/tracks)
- [ ] Implement `trakt_client.py` (watched movies, watched shows, ratings)
- [ ] Extend `run_ingestion.py` to include API sources
- [ ] Write bronze dbt models for Spotify and Trakt (`raw_spotify`, `raw_trakt`)
- [ ] Write pytest tests for API clients (with mocked responses)

**Branch:** `feat/api-ingestion-bronze`

---

## Phase 4 — Silver layer (normalization + deduplication)

- [ ] Write `stg_music.sql` (MusicBuddy primary, Spotify enrichment)
- [ ] Write `stg_books.sql` (BookBuddy + Goodreads, manga detection)
- [ ] Write `stg_movies.sql` (MovieBuddy + Letterboxd + Trakt, anime detection)
- [ ] Write `stg_series.sql` (Trakt shows, anime excluded)
- [ ] Write `stg_anime.sql` (MovieBuddy + Trakt, anime only)
- [ ] Add dbt seeds: `manga_publishers.csv`, `domain_mapping.csv`
- [ ] Implement deduplication logic (canonical ID → rating priority → date)
- [ ] Normalize all ratings to 1–5 integer scale
- [ ] Write dbt schema tests (not_null, unique, accepted_values)

**Branch:** `feat/silver-layer`

---

## Phase 5 — Gold layer (analytical marts)

- [ ] Write `mart_unified_tastes.sql` (full unified view across all domains)
- [ ] Write `mart_ratings.sql` (current rating per item, source-tracked)
- [ ] Write `mart_rating_events.sql` (append-only audit trail)
- [ ] Write `mart_top_rated.sql` (top items per domain, filterable)
- [ ] Write `mart_taste_profile.sql` (aggregate stats: genres, creators, decades)
- [ ] Write dbt schema tests for gold models

**Branch:** `feat/gold-layer`

---

## Phase 6 — FastAPI backend

- [ ] Implement `api/main.py` (FastAPI app, CORS, lifespan)
- [ ] Implement `routers/items.py` (CRUD for taste items)
- [ ] Implement `routers/ratings.py` (add/update rating, triggers `rating_events`)
- [ ] Implement `routers/ingestion.py` (trigger re-ingestion via UI)
- [ ] Implement `routers/stats.py` (data for dashboard widgets)
- [ ] Define Pydantic schemas in `schemas/item.py` and `schemas/rating.py`
- [ ] Write pytest tests for all endpoints

**Branch:** `feat/fastapi-backend`

---

## Phase 7 — CSV templates

- [ ] Create `data/templates/template_music.csv`
- [ ] Create `data/templates/template_books.csv`
- [ ] Create `data/templates/template_manga.csv`
- [ ] Create `data/templates/template_movies.csv`
- [ ] Create `data/templates/template_series.csv`
- [ ] Create `data/templates/template_anime.csv`
- [ ] Write `docs/csv-templates.md` (documentation for each template)

**Branch:** `feat/csv-templates`

---

## Phase 8 — LangGraph agent

- [ ] Implement `sql_tool.py` (natural language → DuckDB SQL via LLM)
- [ ] Implement `rating_tool.py` (add/update rating via FastAPI)
- [ ] Implement `recommend_tool.py` (cross-domain recommendations)
- [ ] Implement `graph.py` (LangGraph agent with state, tools, memory)
- [ ] Write `prompts.py` (system prompts in FR and EN)
- [ ] Implement `agent/app.py` (Chainlit entry point)

**Branch:** `feat/langgraph-agent`

---

## Phase 9 — Evidence.dev dashboard

- [ ] Initialize Evidence.dev project in `dashboard/`
- [ ] Create pages: overview, music, books, manga, movies, series, anime
- [ ] Add widgets: top rated, recently added, taste profile, genre breakdown
- [ ] Connect to DuckDB gold layer

**Branch:** `feat/evidence-dashboard`

---

## Phase 10 — Frontend UI

- [ ] Implement `frontend/index.html` (responsive layout, domain navigation)
- [ ] Implement JS: browse, filter, sort items; star-rating widget; CSV upload
- [ ] Implement i18n: `fr.json`, `en.json`
- [ ] Connect to FastAPI backend

**Branch:** `feat/frontend-ui`

---

## Phase 11 — Docker + deployment

- [ ] Finalize `Dockerfile` (multi-stage build)
- [ ] Finalize `docker-compose.yml` (api, agent, dashboard services)
- [ ] Write `docs/deployment.md` (Coolify + Hetzner setup guide)
- [ ] Configure DuckDB volume persistence

**Branch:** `feat/docker-deployment`

---

## Phase 12 — Documentation + open source

- [ ] Write `README.md` (project overview, quickstart, architecture diagram)
- [ ] Write `docs/data-sources.md` (export instructions per app)
- [ ] Write `docs/contributing.md`
- [ ] Make repository public on GitHub
- [ ] Publish blog post 1: Architecture overview

**Branch:** `feat/documentation`

---

## Backlog / future improvements

- [ ] MyAnimeList API integration
- [ ] OpenLibrary / Google Books cover enrichment
- [ ] Spotify cover art enrichment for albums
- [ ] Multi-user support (separate DuckDB per user, or schema-per-user)
- [ ] Export taste profile as JSON/CSV
- [ ] Recommendation engine using embeddings (sentence-transformers)
- [ ] Public taste profile page (read-only shareable URL)
