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
