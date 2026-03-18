# Contributing to TasteBase

Thanks for your interest in contributing! TasteBase is a personal open-source project —
contributions that improve reliability, documentation, or extend supported data sources
are especially welcome.

---

## Table of contents

- [Getting started](#getting-started)
- [Project structure](#project-structure)
- [Branch and commit conventions](#branch-and-commit-conventions)
- [Pull request process](#pull-request-process)
- [Code standards](#code-standards)
- [Adding a new data source](#adding-a-new-data-source)
- [Reporting issues](#reporting-issues)

---

## Getting started

1. Fork the repository on GitHub
2. Clone your fork locally:

```bash
   git clone https://github.com/YOUR_USERNAME/tastebase.git
   cd tastebase
```

3. Follow the [local setup instructions](../README.md#local-setup) in the README
4. Create a branch for your change (see naming conventions below)

---

## Project structure

Before making changes, read these files:

| File                                | Purpose                                    |
| ----------------------------------- | ------------------------------------------ |
| [`STRUCTURE.md`](../STRUCTURE.md)   | Annotated folder and file tree             |
| [`DECISIONS.md`](../DECISIONS.md)   | All architectural decisions with rationale |
| [`NEXT_STEPS.md`](../NEXT_STEPS.md) | Current roadmap and backlog                |

The project follows a strict **medallion architecture**:

- `ingestion/` loads raw data into DuckDB bronze tables — no transformation
- `transform/` runs dbt to normalize, deduplicate, and build gold marts
- `api/` is the **only** layer that reads from and writes to DuckDB
- Frontend and agent never access DuckDB directly

---

## Branch and commit conventions

### Branch naming

```
feat/scope-description      # new feature
fix/scope-description       # bug fix
docs/scope-description      # documentation only
refactor/scope-description  # no behaviour change
test/scope-description      # tests only
```

Examples:

```
feat/myanimelist-ingestion
fix/stg-anime-detection
docs/letterboxd-export-guide
```

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(ingestion): add MyAnimeList CSV loader
fix(silver): correct anime detection in stg_anime
docs(data-sources): add Letterboxd export instructions
test(api): add endpoint tests for DELETE /items
refactor(agent): extract sql_tool prompt to prompts.py
```

---

## Pull request process

1. Make sure all tests pass before opening a PR:

```bash
   # Python tests
   pytest tests/ -v

   # dbt tests (from transform/ with env vars exported)
   set -a && source ../.env && set +a
   dbt test
```

2. Open a PR against the `main` branch with:
   - A clear title using the commit convention above
   - A description explaining **what** changed and **why**
   - A reference to any related issue (e.g. `Closes #42`)

3. If your change introduces a new architectural or technical decision, add an entry
   to `DECISIONS.md` following the existing format:

```markdown
### DEC-XXX — Short title

**Date:** Month, Year
**Status:** Accepted

**Context:** ...
**Options considered:** ...
**Decision:** ...
**Rationale:** ...
```

4. If your change adds, moves, or renames files, update `STRUCTURE.md`.

5. PRs are reviewed by the maintainer. Expect feedback within a few days.

---

## Code standards

### Python

- **Python 3.12+** — no compatibility shims for older versions
- **Type annotations** on all function signatures
- **Google Style docstrings** on all public functions and classes
- **Black** for formatting, **Ruff** for linting
- All secrets via environment variables — never hardcoded
- All identifiers, comments, and docstrings in **English**

```python
def normalize_rating(raw_rating: float | None, scale: float = 5.0) -> int | None:
    """Normalize a raw float rating to the unified 1–5 integer scale.

    Args:
        raw_rating: The source rating value. None means unrated.
        scale: The maximum value of the source scale. Defaults to 5.0.

    Returns:
        Integer rating in [1, 5], or None if the item is unrated.
    """
    if raw_rating is None or raw_rating == 0:
        return None
    return max(1, min(5, round(raw_rating * 5.0 / scale)))
```

### SQL / dbt

- Bronze models: `raw_` prefix, materialized as `table`, raw data only — no transformation
- Silver models: `stg_` prefix, materialized as `view`, normalized and deduplicated
- Gold models: `mart_` prefix, materialized as `table` or `incremental`
- Always use `{{ ref() }}` to reference upstream models — never hardcode table names
- Add `not_null` and `unique` schema tests for primary keys in `schema.yml`
- Ratings are normalized to 1–5 integers **only at the silver layer** — never before

### Vue 3 / JavaScript

- Composition API (`<script setup>`) — no Options API
- All UI strings via `vue-i18n` — no hardcoded French or English in templates
- API calls go through `src/api/` modules only — never `fetch`/`axios` directly in components

---

## Adding a new data source

Adding a new CSV source (e.g. MyAnimeList) requires changes in three layers:

### 1. Ingestion — `ingestion/csv/`

Create `ingestion/csv/myanimelist_loader.py` extending `BaseLoader`:

```python
class MyAnimeListLoader(BaseLoader):
    def validate(self) -> None:
        # Check required columns
        ...

    def _parse(self) -> pd.DataFrame:
        # Read CSV, rename columns, cast types
        ...
```

Register it in `ingestion/run_ingestion.py`.

### 2. Bronze — `transform/models/bronze/`

Create `raw_myanimelist.sql`:

```sql
{{ config(materialized='table') }}
SELECT * FROM main.raw_myanimelist
```

### 3. Silver — extend or create a staging model

If the new source maps to an existing domain (e.g. anime → `stg_anime`), add a CTE
for the new source and include it in the `UNION ALL`. If it introduces a new domain,
create a new `stg_<domain>.sql` model.

### 4. Tests

Add a pytest test file in `tests/ingestion/` using a sample CSV fixture.
Add dbt schema tests in `transform/models/bronze/schema.yml` and the relevant
silver `schema.yml`.

### 5. Documentation

Add an entry to [`docs/data-sources.md`](data-sources.md) with export instructions.
Update [`STRUCTURE.md`](../STRUCTURE.md) with the new files.
Add a `DECISIONS.md` entry if any architectural choice was made.

---

## Reporting issues

Open a [GitHub issue](https://github.com/jeremy6680/tastebase/issues) with:

- A clear title describing the problem
- Steps to reproduce (include your OS, Python version, and relevant env var values — **never your actual API keys**)
- The expected behaviour and the actual behaviour
- Relevant error output (log lines, stack trace, dbt error message)

For feature requests, describe the use case, not just the feature.
