# DECISIONS.md — TasteBase

> Log of architectural and technical decisions.
> Each entry follows the format: **context → options considered → decision → rationale**.
> Most recent decisions at the top of each section.

---

## Infrastructure & deployment

### DEC-039 — Ingestion writes to tmp/warehouse.duckdb to preserve dbt catalog name

**Date:** 2026-04-28
**Status:** Accepted

**Context:** dbt-duckdb derives the catalog name from the database file stem. Using
`warehouse.duckdb.tmp` as the temp path caused dbt to fail with `Catalog "warehouse.duckdb"
does not exist!` — the stem `warehouse.duckdb` does not match the `warehouse` catalog
expected by the models.

**Decision:** The ingestion process writes to `data/tmp/warehouse.duckdb` — a subdirectory
with the same filename. This preserves the `warehouse` catalog name. On success,
`data/tmp/warehouse.duckdb` atomically replaces `data/warehouse.duckdb` via `shutil.move`.
The `tmp/` directory is created automatically; its contents are gitignored.

**Rationale:** Keeping the same filename stem in a subdirectory is the minimal change that
satisfies both constraints: isolation from the API's live database, and catalog name
compatibility with dbt models.

---

### DEC-038 — Ingestion uses a temporary database to avoid DuckDB write lock

**Date:** 2026-04-28
**Status:** Accepted

**Context:** The API process (uvicorn, PID 1 in Docker) holds a DuckDB write lock on
`warehouse.duckdb` from startup. When `POST /ingest/upload` triggers a subprocess to run
`run_ingestion.py`, the subprocess tries to open the same file in write mode. DuckDB's
single-writer constraint causes `IO Error: Could not set lock on file`.

**Decision:** The ingestion pipeline writes to a completely separate file
(`data/tmp/warehouse.duckdb`, see DEC-039). The API never touches the tmp file. On success,
the tmp file replaces the main database via `shutil.move`. The API's read-only connections
to `warehouse.duckdb` are never blocked.

**Rationale:** DuckDB's single-writer model is a hard constraint. Writing to a separate
file is the only approach that eliminates lock conflicts entirely.

---

### DEC-037 — get_db() uses read_only=True; get_db_write() for write endpoints

**Date:** 2026-04-28
**Status:** Accepted

**Context:** `api/dependencies.py` originally opened all connections in `read_only=False`.
This held an exclusive write lock during every request, blocking the ingestion subprocess.

**Decision:** Split into two dependency functions:

- `get_db()` → `read_only=True` — used by all GET endpoints
- `get_db_write()` → `read_only=False` — used only by `upsert_rating`, `upsert_category`,
  `batch_upsert_categories`

**Rationale:** Read-only connections release the write lock entirely. The split follows
the principle of least privilege.

---

### DEC-036 — API lifespan skips ensure_table when warehouse.duckdb does not exist

**Date:** 2026-04-28
**Status:** Accepted

**Context:** On fresh deployments, `warehouse.duckdb` does not yet exist. The lifespan
hook opening a write connection created the file and registered PID 1 as write lock owner,
blocking the first ingestion run.

**Decision:** `ensure_table` is guarded by `os.path.exists(db_path)`. Skipped on first
boot; runs normally on subsequent API restarts once data exists.

---

## Data architecture

### DEC-001 — DuckDB over PostgreSQL

**Date:** Feb, 2026
**Status:** Accepted

**Decision:** DuckDB — zero infrastructure, single-file, analytical SQL, native Python/dbt integration.

---

### DEC-002 — Medallion architecture (bronze / silver / gold)

**Date:** Feb, 2026
**Status:** Accepted

**Decision:** Three-layer medallion via dbt-duckdb. Bronze = immutable raw. Silver = normalized + deduplicated. Gold = analytical marts.

---

### DEC-003 — Deduplication at the silver layer, not bronze

**Date:** Feb, 2026
**Status:** Accepted

**Decision:** Deduplicate in silver (`stg_` models) using canonical IDs (ISBN13, IMDB ID, Discogs ID).

---

### DEC-004 — Unified 1–5 integer rating scale

**Date:** Feb, 2026
**Status:** Accepted

**Decision:** Normalize all ratings to integer 1–5 at silver. `NULL` for unrated (never 0).

Conversion: float 0–5 → `ROUND()`, Letterboxd → `ROUND()`, Trakt 1–10 → `CEIL(rating/2.0)`.

---

### DEC-005 — MusicBuddy as the primary music source

**Date:** Feb, 2026
**Status:** Accepted

**Decision:** MusicBuddy CSV is primary. Spotify is enrichment-only (cover art, Spotify ID).

---

### DEC-006 — Deduplication priority rules

**Date:** Feb, 2026
**Status:** Accepted

**Decision:** 1) Keep entry with a rating. 2) Higher rating wins. 3) Oldest entry if neither rated.

---

### DEC-030 — mart_ratings switched to incremental materialization

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** `mart_ratings` uses incremental materialization. Existing rows (user ratings) survive all pipeline rebuilds.

---

### DEC-031 — CSV upload saves to canonical filename; pipeline always runs in full

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** Uploaded files saved under canonical filename. Full pipeline always runs after upload.

---

### DEC-032 — Spotify httpx calls capped at 30s timeout; Retry-After > 60s skips the client

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** 30s timeout on all httpx calls. `Retry-After > 60s` → skip Spotify gracefully.

---

## Tech stack

### DEC-007 — dbt-duckdb over raw SQL scripts

**Date:** Feb, 2026
**Status:** Accepted

**Decision:** dbt-duckdb for all transformations (lineage, schema tests, incremental models).

---

### DEC-008 — LangGraph over CrewAI or plain LangChain

**Date:** Feb, 2026
**Status:** Accepted

**Decision:** LangGraph — explicit state machine, fine-grained control, better for stateful single-agent use case.

---

### DEC-009 — Chainlit for agent UI

**Date:** Feb, 2026
**Status:** Accepted

**Decision:** Chainlit — purpose-built for conversational AI, native LangGraph integration.

---

### DEC-010 — Evidence.dev for the dashboard (superseded by DEC-035)

**Date:** Feb, 2026
**Status:** Superseded

**See DEC-035.** Evidence.dev replaced by Vue 3 Insights pages (Chart.js).

---

### DEC-011 — FastAPI as the only DuckDB access layer

**Date:** Feb, 2026
**Status:** Accepted

**Decision:** All DuckDB reads/writes go through FastAPI. Frontend and agent never touch DuckDB directly.

---

### DEC-012 — mart_rating_events is append-only

**Date:** Feb, 2026
**Status:** Accepted

**Decision:** `mart_rating_events` is append-only. Rows are never updated or deleted.

---

## i18n

### DEC-013 — French as the default language

**Date:** Feb, 2026
**Status:** Accepted

**Decision:** French is default. English supported. Strings in `fr.json` / `en.json`.

---

### DEC-014 — Fixed canonical filenames for CSV sources

**Date:** Mar, 2026
**Status:** Accepted

| Source     | Expected file             |
| ---------- | ------------------------- |
| MusicBuddy | `data/raw/musicbuddy.csv` |
| BookBuddy  | `data/raw/bookbuddy.csv`  |
| Goodreads  | `data/raw/goodreads.csv`  |
| MovieBuddy | `data/raw/moviebuddy.csv` |
| Letterboxd | `data/raw/letterboxd.csv` |

---

### DEC-015 — Audit columns injected at the bronze layer

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** `_source` and `_loaded_at` added by `BaseLoader` to every bronze row.

---

### DEC-016 — BaseApiClient separated from BaseLoader

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** Separate `base_api_client.py` for API sources. Shares `load()` interface but not CSV-specific methods.

---

### DEC-017 — DUCKDB_PATH must be absolute in .env

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** `DUCKDB_PATH` must be an absolute path. dbt resolves relative paths from `transform/`.

---

### DEC-018 — raw_spotify pre_hook for missing source table

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** `pre_hook` in `raw_spotify.sql` creates `main.raw_spotify` as empty table if missing.

---

### DEC-019 — Anime detection limited to genres LIKE '%anime%' (known gap)

**Date:** Mar, 2026
**Status:** Accepted (with known limitation)

**Decision:** MovieBuddy exports "Animation" not "Anime" (TMDB). Fix via production country or curated seed is backlog.

---

### DEC-020 — Per-request DuckDB connection via FastAPI Depends

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** Per-request connections via `get_db` / `get_db_write` (see DEC-037).

---

### DEC-021 — subprocess for dbt invocation in POST /ingest

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** `subprocess.run(["dbt", "run"], cwd=transform/)` with `capture_output=True`.

---

### DEC-022 — In-memory DuckDB for API test isolation

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** In-memory DuckDB injected via `app.dependency_overrides[get_db]` in `tests/api/conftest.py`.

---

### DEC-023 — Rating tool split into search + submit

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** Two tools: `search_item_for_rating` + `submit_rating`. User confirmation required between them.

---

### DEC-024 — sys.path fix in agent/app.py

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** `sys.path.insert(0, str(Path(__file__).parent.parent))` at top of `agent/app.py`.

---

### DEC-025 — Evidence.dev requires DuckDB file physically in sources/ (superseded)

**Date:** Mar, 2026
**Status:** Superseded — See DEC-035.

---

### DEC-026 — Evidence pages guard empty datasets (superseded)

**Date:** Mar, 2026
**Status:** Superseded — See DEC-035.

---

### DEC-027 — mart_item_categories as a satellite table outside the dbt pipeline

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** `mart_item_categories` in `main_gold`, created via `CREATE TABLE IF NOT EXISTS`
in the FastAPI lifespan. Survives all `dbt run` rebuilds.

---

### DEC-028 — Vue 3 + Vite as the frontend stack

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** Vue 3 (Composition API, SFC) + Vite, vue-router, vue-i18n, axios, SCSS.
No component library. Custom design system via SCSS tokens.

---

### DEC-029 — Hard delete for manually created items

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** Hard delete via `DELETE /items/{item_id}`. dbt-managed items reappear on next `dbt run` — by design.

---

### DEC-033 — Agent model configurable via AGENT_MODEL env var

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** All `_get_llm()` calls read from `os.environ.get("AGENT_MODEL", "claude-haiku-4-5-20251001")`.

---

### DEC-034 — Chainlit streaming: suppress pre-tool tokens, collect final answer from on_chain_end

**Date:** Mar, 2026
**Status:** Accepted

**Decision:** Token streaming disabled. Final answer from `on_chain_end`. `AIMessage.content`
normalized via `_extract_text()`.

---

### DEC-035 — Evidence.dev removed; Coolify split into two independent apps; frontend on Netlify

**Date:** 2026-04
**Status:** Accepted

**Context:** Evidence.dev required a physical DuckDB file in the container, causing
cascading failures. Deploying all services in a single Coolify app caused cascading health
check failures. Coolify's `docker buildx bake` passes all env vars as `--build-arg`,
which BuildKit rejects unless `ARG` is declared — fixed with `args: {}` in compose files.

**Decision:**

1. Evidence.dev removed. Insights section added to Vue 3 frontend (Chart.js / vue-chartjs):
   domain donut, rating distribution, decades stacked bar, top creators horizontal bar.
2. Coolify split into two apps using repo-root compose files:
   - `tastebase-api` → `docker-compose.api.yml`
   - `tastebase-agent` → `docker-compose.agent.yml`
3. Vue 3 frontend deployed on Netlify (`frontend/netlify.toml`).

**Key production env vars:**

- `tastebase-api`: `FRONTEND_URL`, `TASTEBASE_AGENT_URL` (CORS), `DUCKDB_PATH=/app/data/warehouse.duckdb`
- `tastebase-agent`: `API_BASE_URL=https://api.tastebase.jeremymarchandeau.com`
- Netlify: `VITE_API_BASE_URL`, `VITE_AGENT_URL`

---
