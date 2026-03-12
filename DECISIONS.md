# DECISIONS.md — TasteBase

> Log of architectural and technical decisions.
> Each entry follows the format: **context → options considered → decision → rationale**.
> Most recent decisions at the top of each section.

---

## Data architecture

### DEC-001 — DuckDB over PostgreSQL

**Date:** Feb, 2026  
**Status:** Accepted

**Context:** The project needs a database for personal-scale data (thousands of items, not millions). It runs on a single VPS and must be portable and easy to back up.

**Options considered:**

- PostgreSQL: robust, widely supported, requires a running server process
- SQLite: simpler, but weak analytical SQL support (no `ARRAY`, limited window functions)
- DuckDB: serverless, single-file, full analytical SQL, native Python integration

**Decision:** DuckDB.

**Rationale:** Zero infrastructure overhead, single file backup, excellent analytical SQL (window functions, `LIST_AGG`, `ARRAY`, `STRUCT`), native Python and dbt integration. Perfectly sized for personal data volume.

---

### DEC-002 — Medallion architecture (bronze / silver / gold)

**Date:** Feb, 2026  
**Status:** Accepted

**Context:** Data comes from heterogeneous sources with different schemas, rating scales, and domain signals. Transformations need to be traceable and testable.

**Options considered:**

- Single flat table: simple but unmaintainable
- Two layers (raw + clean): adequate but no separation between dedup/normalization and analytical marts
- Three layers (bronze / silver / gold): standard analytics engineering pattern

**Decision:** Three-layer medallion via dbt-duckdb.

**Rationale:** Bronze keeps raw data immutable (audit trail). Silver normalizes and deduplicates. Gold exposes clean marts for the agent and dashboard. Each layer is independently testable and versioned in SQL.

---

### DEC-003 — Deduplication at the silver layer, not bronze

**Date:** Feb, 2026  
**Status:** Accepted

**Context:** The same item (e.g. an album) can appear in multiple sources (MusicBuddy + Spotify). Deduplication must happen somewhere.

**Decision:** Deduplicate in silver (`stg_` models), using canonical IDs (ISBN13, IMDB ID, Discogs ID) as the primary join key.

**Rationale:** Bronze stays as an immutable raw log. Deduplication logic lives in version-controlled, testable SQL. If the logic changes, bronze data is unaffected and silver can be rebuilt from scratch.

---

### DEC-004 — Unified 1–5 integer rating scale

**Date:** Feb, 2026  
**Status:** Accepted

**Context:** Sources use different rating scales:

- MusicBuddy / BookBuddy / MovieBuddy: float 0.0–5.0
- Goodreads: integer 0–5
- Letterboxd: float 0.5–5.0 by 0.5 increments
- Trakt.tv: integer 1–10

**Decision:** Normalize all ratings to integer 1–5 at the silver layer. Store `NULL` for unrated items (never `0`).

**Conversion rules:**

- Float 0.0–5.0 → `ROUND()`, then `NULL` if result = 0
- Letterboxd 0.5–5.0 → `ROUND()` to nearest integer
- Trakt 1–10 → `CEIL(rating / 2.0)`

**Rationale:** A single scale enables cross-domain comparison and simplifies the agent's reasoning. Rounding is applied only once, at silver, and never again downstream.

---

### DEC-005 — MusicBuddy as the primary music source

**Date:** Feb, 2026  
**Status:** Accepted

**Context:** Both MusicBuddy (CSV) and Spotify (API) provide music data. They must be merged without losing user ratings.

**Decision:** MusicBuddy CSV is the primary music source. Spotify is enrichment-only (cover art, Spotify ID, play counts). Ratings from MusicBuddy always take precedence.

**Rationale:** MusicBuddy contains user-curated ratings. Spotify's saved albums have no native rating. Merging should enrich MusicBuddy entries, not replace them.

---

### DEC-006 — Deduplication priority rules

**Date:** Feb, 2026  
**Status:** Accepted

**Context:** When the same item exists in multiple sources, one version must be kept.

**Decision:** Priority order:

1. Keep the entry **with a rating** (rating > 0 / not NULL)
2. If both have ratings, keep the **higher rating**
3. If neither has a rating, keep the **oldest entry** (earliest `date_added`)

**Rationale:** A user-supplied rating is more valuable than no rating. A higher rating is preferred because it more likely reflects a deliberate user choice. Oldest entry preserves the original discovery date.

---

## Tech stack

### DEC-007 — dbt-duckdb over raw SQL scripts

**Date:** Feb, 2026  
**Status:** Accepted

**Context:** Transformations need to be maintainable, testable, and documented.

**Decision:** dbt-duckdb for all transformations.

**Rationale:** dbt provides data lineage, built-in schema tests (`not_null`, `unique`, `accepted_values`), auto-generated docs, and incremental models. It's a standard analytics engineering tool that also demonstrates professional skills for the portfolio.

---

### DEC-008 — LangGraph over CrewAI or plain LangChain

**Date:** Feb, 2026  
**Status:** Accepted

**Context:** The conversational agent needs to manage state across turns and call multiple tools (SQL, rating, recommendation).

**Options considered:**

- Plain LangChain: adequate for simple chains, weak for stateful multi-turn conversations
- CrewAI: designed for multi-agent workflows, overkill for a single-agent use case
- LangGraph: explicit state machine, fine-grained control over nodes and edges

**Decision:** LangGraph.

**Rationale:** TasteBase needs a single agent with memory, not a multi-agent crew. LangGraph's explicit state graph makes the agent's behavior predictable and debuggable. It also allows structured SQL tool calls with validated outputs.

---

### DEC-009 — Chainlit for agent UI

**Date:** Feb, 2026  
**Status:** Accepted

**Context:** The agent needs a chat interface.

**Options considered:**

- Streamlit: general-purpose, requires more work for a chat-first UI
- Gradio: similar limitations
- Custom React frontend: full control but significant development overhead
- Chainlit: purpose-built for conversational AI UIs, integrates natively with LangGraph

**Decision:** Chainlit.

**Rationale:** Chainlit provides streaming, message threading, user sessions, and LangGraph integration out of the box. It reduces frontend work to near-zero for the agent UI.

---

### DEC-010 — Evidence.dev for the dashboard

**Date:** Feb, 2026  
**Status:** Accepted

**Context:** The project needs a read-only analytics dashboard.

**Options considered:**

- Streamlit: Python-native but requires a server, mixes UI and logic
- Metabase: full-featured but heavyweight for personal use
- Evidence.dev: markdown + SQL, generates a static site, dbt-native

**Decision:** Evidence.dev.

**Rationale:** Evidence.dev reads DuckDB directly, integrates with dbt, and compiles to a static site (easy to deploy on Coolify). Writing dashboards in markdown + SQL is a clean, low-overhead pattern that fits the project's "code-first" philosophy.

---

### DEC-011 — FastAPI as the only DuckDB access layer

**Date:** Feb, 2026  
**Status:** Accepted

**Context:** Both the frontend and the LangGraph agent need to read/write data.

**Decision:** All DuckDB reads and writes go through FastAPI endpoints. The frontend and the agent never connect to DuckDB directly.

**Rationale:** A single access layer enforces consistent validation (Pydantic), handles concurrent access safely, and makes the API independently testable. It also makes the agent's tool calls explicit HTTP calls, which are easier to log and debug.

---

### DEC-012 — `gold_rating_events` is append-only

**Date:** Feb, 2026  
**Status:** Accepted

**Context:** User ratings can change over time. The history of changes is valuable for the taste profile and for debugging.

**Decision:** `mart_rating_events` (gold) is append-only. Every rating change inserts a new row with `old_rating`, `new_rating`, `changed_by`, and `changed_at`. Rows are never updated or deleted.

**Rationale:** An immutable event log enables full audit trail, time-travel queries ("what did I rate this in 2023?"), and future trend analysis. It follows the event sourcing pattern standard in data engineering.

---

## i18n

### DEC-013 — French as the default language

**Date:** Feb, 2026  
**Status:** Accepted

**Context:** Jeremy is French and uses the app personally. The app will also be open-sourced for a broader audience.

**Decision:** French is the default language. English is a supported alternative. All translation strings live in `frontend/i18n/fr.json` and `frontend/i18n/en.json`. Agent prompts are available in both languages in `agent/prompts.py`.

**Rationale:** French-first reflects the author's primary use case. English support makes the project accessible internationally and aligns with the open-source goal.

---

### DEC-014 — Fixed canonical filenames for CSV sources

**Date:** Mar, 2026
**Status:** Accepted

**Context:** Buddy+ apps and Letterboxd export files with names that
include timestamps (e.g. `MusicBuddy 2026-03-05 144228`,
`letterboxd-username-2026-03-05-16-05-utc/ratings.csv`). Loaders need
a predictable filename to operate without configuration.

**Decision:** Each source has a fixed canonical filename that the user
must use:

| Source     | Expected file             |
| ---------- | ------------------------- |
| MusicBuddy | `data/raw/musicbuddy.csv` |
| BookBuddy  | `data/raw/bookbuddy.csv`  |
| Goodreads  | `data/raw/goodreads.csv`  |
| MovieBuddy | `data/raw/moviebuddy.csv` |
| Letterboxd | `data/raw/letterboxd.csv` |

Renaming instructions are documented in `docs/data-sources.md`.

**Rationale:** A fixed name per source keeps loader code simple (no
glob patterns, no dynamic file discovery) and makes behavior
predictable. The renaming constraint is lightweight and clearly
documented.

---

### DEC-015 — Audit columns injected at the bronze layer

**Date:** Mar, 2026
**Status:** Accepted

**Context:** In the silver layer, multiple sources are merged into a
single model (e.g. BookBuddy + Goodreads → stg_books). Without
explicit traceability, it becomes impossible to know where a row
originated after a join.

**Decision:** Two audit columns are added by `BaseLoader` to every row
before writing to bronze:

- `_source` (VARCHAR): source identifier, e.g. `"musicbuddy"`
- `_loaded_at` (TIMESTAMP WITH TIME ZONE): UTC timestamp of the ingestion run

The `_` prefix follows the dbt convention for technical metadata columns.
Injection happens in `BaseLoader.load()`, after `_parse()` returns, so
no concrete loader ever needs to handle it.

**Rationale:** Source-to-gold traceability is essential for debugging
deduplication and auditing imported ratings. Centralizing injection in
`BaseLoader` makes it impossible for any loader to accidentally omit
these columns.

---

### DEC-016 — BaseApiClient separated from BaseLoader

**Date:** Mar, 2026
**Status:** Accepted

**Context:** API clients (Spotify, Trakt) initially inherited from `BaseLoader`,
but `BaseLoader` enforces three constraints that are incompatible with API sources:

- `__init__` requires a `file_path` (API sources have no file on disk)
- `validate()` is abstract and oriented toward CSV file validation
- `_parse()` returns a `pd.DataFrame` (API clients return a `list[dict]`)

**Decision:** Create `ingestion/base_api_client.py` — a separate abstract base class
that shares only what is common to both loader types: audit column injection
(`_source`, `_loaded_at`), scoped logging, and a consistent `load()` interface.

Abstract methods defined in `BaseApiClient`:

- `_parse() -> list[dict]`: fetch from API and return raw records
- `_write_to_bronze(records)`: write records to the DuckDB bronze table

**Rationale:** Follows the Interface Segregation Principle — API clients should not
be required to implement `validate()` or accept a `file_path` that has no meaning
for them. Both classes share the same observable contract (`load()`, audit columns)
without artificial coupling.

---

### DEC-017 — DUCKDB_PATH must be absolute in .env

**Date:** Mar, 2026
**Status:** Accepted

**Context:** dbt resolves relative paths from the directory it is executed in
(`transform/`), not from the project root. Setting `DUCKDB_PATH=data/warehouse.duckdb`
in `.env` causes dbt to look for `transform/data/warehouse.duckdb`, which does
not exist.

**Decision:** `DUCKDB_PATH` must always be set as an absolute path in `.env`.
The fallback value in `profiles.yml` has been removed to force an explicit error
if the variable is missing, rather than silently resolving to the wrong path.

**Rationale:** A missing-variable error is easier to diagnose than a
"file not found" error pointing to a non-existent nested path. Absolute paths
eliminate ambiguity regardless of the working directory.

---

### DEC-018 — raw_spotify pre_hook for missing source table

**Date:** Mar, 2026
**Status:** Accepted

**Context:** `raw_spotify.sql` reads from `main.raw_spotify`, which is created
by `SpotifyClient.load()`. When Spotify is rate-limited and ingestion hasn't run,
`main.raw_spotify` does not exist, causing `dbt run --select raw_spotify` to fail.
A self-referencing fallback in the model caused a DAG cycle error.

**Decision:** Use a dbt `pre_hook` in `raw_spotify.sql` to create `main.raw_spotify`
as an empty table if it does not exist, before the SELECT runs.

**Rationale:** The pre_hook runs before the model's SELECT, breaking the cycle.
Downstream silver models (`stg_music`) can reference `raw_spotify` safely via
`{{ ref() }}` regardless of whether Spotify has been ingested. When Spotify
ingestion runs, `make ingest` populates `main.raw_spotify` and the next
`dbt run` propagates the data automatically.

---

### DEC-019 — Anime detection limited to genres LIKE '%anime%' (known gap)

**Date:** Mar, 2026
**Status:** Accepted (with known limitation)

**Context:** MovieBuddy exports genre metadata from TMDB, which uses
"Animation" as a genre — not "Anime". The `stg_anime.sql` model filters on
`LOWER(genres) LIKE '%anime%'`, which produces 0 rows against real MovieBuddy
exports.

**Decision:** Keep the current signal as the primary detection mechanism.
Document the limitation. Plan enrichment via production country (JP) or a
curated anime titles seed as a backlog item.

**Rationale:** Changing the detection to `LIKE '%animation%'` would produce
false positives (e.g. Pixar films, western cartoons). A dedicated anime seed
or country-based enrichment is the correct long-term fix. The current state
is a known gap, not a bug.

---

### DEC-020 — Per-request DuckDB connection via FastAPI Depends

**Date:** Mar, 2026
**Status:** Accepted

**Context:** FastAPI needs a safe way to access DuckDB across concurrent
requests. DuckDB in single-file mode does not support multiple simultaneous
writers safely.

**Options considered:**

- Shared connection via lifespan (`app.state.db`): simple, but risks
  concurrent write conflicts and complicates test isolation.
- Global module-level connection: same concurrency problem, harder to override
  in tests.
- Per-request connection via `contextmanager` + `Depends`: each request opens
  and closes its own connection; safe for the expected single-user load.

**Decision:** Per-request connection injected via `api/dependencies.py:get_db`
using FastAPI's `Depends` mechanism.

**Rationale:** Eliminates concurrent write conflicts on the single-file
database. The `Depends` pattern makes the connection trivially replaceable
in tests (override `get_db` in `conftest.py` to inject an in-memory DuckDB).
Connection overhead is negligible at personal-data scale.

---

### DEC-021 — subprocess for dbt invocation in POST /ingest

**Date:** Mar, 2026
**Status:** Accepted

**Context:** The `/ingest` endpoint needs to trigger a `dbt run` after
CSV/API ingestion completes.

**Options considered:**

- `dbt-core` Python API: internal, undocumented as a public interface, has
  broken between minor versions.
- `subprocess.run(["dbt", "run"])`: the approach recommended by dbt for
  external integrations; stable across versions.

**Decision:** `subprocess.run(["dbt", "run"], cwd=transform/)` with
`capture_output=True`.

**Rationale:** The subprocess approach is stable, predictable, and produces
the same output as running dbt manually. Both stdout and stderr are captured
and returned in the `IngestionResult` response, making failures easy to
diagnose from the API response alone.

---

### DEC-022 — In-memory DuckDB for API test isolation

**Date:** Mar, 2026
**Status:** Accepted

**Context:** API tests need an isolated database that does not touch the
real warehouse file.

**Options considered:**

- Mock the `get_db` dependency with `unittest.mock`: fast, but does not
  exercise any SQL logic.
- Temporary file-based DuckDB: exercises SQL but requires cleanup and risks
  interference between parallel test runs.
- In-memory DuckDB with gold schema bootstrapped in `conftest.py`: exercises
  real SQL, fully isolated, zero cleanup required.

**Decision:** In-memory DuckDB connection injected via `app.dependency_overrides[get_db]`
in `tests/api/conftest.py`. The fixture creates the gold schema tables and
seeds one item per domain before each test.

**Rationale:** Tests exercise the real SQL queries against a realistic schema
without any mocking of database logic. Each test gets a fresh state.
The override pattern is the idiomatic FastAPI approach for dependency
substitution in tests.
