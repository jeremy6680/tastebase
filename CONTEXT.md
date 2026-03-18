# CONTEXT.md — TasteBase

> **Personal AI-powered taste warehouse** — A full-stack data engineering project that centralizes a user's cultural preferences (music, books, manga, movies, series, anime) into a DuckDB warehouse, exposes them through a dashboard, and makes them queryable via a LangGraph AI agent.

---

## Project Overview

**Name:** TasteBase  
**Repository:** https://github.com/jeremy6680/tastebase (public, initially private)  
**Author:** Jeremy Marchandeau  
**Blog:** web2data.jeremymarchandeau.com  
**Deployment:** Coolify + Hetzner VPS  
**Status:** In development

### What it does

1. Ingests cultural taste data from multiple sources (CSV exports from Buddy+ apps, Goodreads, Letterboxd, Spotify API, Trakt.tv API)
2. Stores everything in a local DuckDB warehouse using a medallion architecture (bronze/silver/gold)
3. Deduplicates items across sources using canonical IDs (ISBN, IMDB, TMDB, Discogs)
4. Exposes a web UI (Streamlit or Chainlit) for browsing, filtering, sorting, and rating items (1–5 stars)
5. Powers a LangGraph AI agent that answers natural-language questions and generates cross-domain recommendations

### Why it exists

- Portfolio project demonstrating analytics engineering + AI engineering skills
- Personal tool replacing multiple fragmented apps with a single queryable source of truth
- Open-source template others can adapt for their own taste data
- Content for a Web2Data blog series

---

## Architecture

```
data/raw/           ← CSV exports (gitignored, user-supplied)
ingestion/          ← Python scripts: CSV loaders + API clients (Spotify, Trakt)
transform/          ← dbt-duckdb project (bronze → silver → gold)
agent/              ← LangGraph agent with SQL, rating, and recommendation tools
dashboard/          ← Evidence.dev (or Streamlit) visualization
app/                ← Main web application (FastAPI backend + frontend)
docker/             ← Dockerfile + docker-compose for Coolify deployment
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
      ↓                    ↓
 Evidence.dev          LangGraph Agent
 Dashboard             (Chainlit UI)
```

---

## Domain Taxonomy

Six content domains, each with its own silver model:

| Domain   | Sources                                      | Detection method                                           |
| -------- | -------------------------------------------- | ---------------------------------------------------------- |
| `music`  | MusicBuddy CSV, Spotify API                  | `Content Type = Album`                                     |
| `book`   | BookBuddy CSV, Goodreads CSV                 | Category/Tags/Publisher heuristics                         |
| `manga`  | BookBuddy CSV, Goodreads CSV                 | Keywords: manga/manhwa/bande dessinée + publisher list     |
| `movie`  | MovieBuddy CSV, Letterboxd CSV, Trakt.tv API | `Content Type = Movie`, Trakt `type=movie`                 |
| `series` | Trakt.tv API                                 | Trakt `type=show`, genre ≠ Anime                           |
| `anime`  | MovieBuddy CSV, Trakt.tv API                 | Genre contains "Anime", or Trakt `type=show` + genre=Anime |

---

## Source Schemas

### goodreads.csv

Key columns: `Book Id`, `Title`, `Author`, `ISBN`, `ISBN13`, `My Rating` (0–5), `Year Published`, `Date Read`, `Date Added`, `Bookshelves`, `Exclusive Shelf`

- Rating: 0–5 integer (0 = unrated) → keep as-is, convert 0 to NULL
- Domain detection: check `Bookshelves` for manga/bd/comic keywords

### bookbuddy.csv (Kimico BookBuddy)

Key columns: `Title`, `Author`, `ISBN`, `Rating` (0.0–5.0 float), `Year Published`, `Date Added`, `Tags`, `Category`, `Status`, `Genre`, `Publisher`

- Rating: float 0.0–5.0 → ROUND(), 0.0 = NULL
- Domain detection: `Category` or `Tags` for manga keywords, `Publisher` for known manga publishers

### letterboxd.csv

Key columns: `Date`, `Name`, `Year`, `Letterboxd URI`, `Rating` (0.5–5.0 by 0.5)

- Rating: 0.5–5.0 → ROUND() to nearest integer
- Always `movie` domain

### moviebuddy.csv (Kimico MovieBuddy)

Key columns: `Title`, `Content Type` (Movie/TV Show), `Genres`, `Release Year`, `IMDB ID`, `TMDB ID`, `Rating` (0.0–5.0 float), `Date Added`, `Status`, `Directors`, `Cast`, `Summary`

- Rating: float 0.0–5.0 → ROUND(), 0.0 = NULL
- Domain: `Content Type = Movie` → movie, `Content Type = TV Show` → series or anime (check Genres)

### musicbuddy.csv (Kimico MusicBuddy)

Key columns: `Title`, `Artist`, `Release Year`, `Genres`, `Rating` (0.0–5.0 float), `Date Added`, `Discogs Release ID`, `UPC-EAN13`, `Content Type` (Album)

- Rating: float 0.0–5.0 → ROUND(), 0.0 = NULL
- Always `music` domain

### Spotify API

Endpoints: recently played, saved albums, top artists, top tracks  
No native rating → rating defaults to NULL (user assigns via app UI)

### Trakt.tv API

Endpoints: watched movies, watched shows, ratings

- Rating: 1–10 integer → `CEIL(rating / 2.0)` to convert to 1–5
- Domain detection: `type=movie` → movie, `type=show` + genre=Anime → anime, `type=show` → series

---

## Deduplication Rules

Priority order when the same item appears in multiple sources:

1. Keep the entry **with a rating > 0** (or > 0.0)
2. If both have ratings, keep the **higher rating** (user-supplied takes priority over imported)
3. If neither has a rating, keep the **oldest entry** (earliest `date_added`)

Matching keys by domain:

| Domain             | Primary key | Fallback key                            |
| ------------------ | ----------- | --------------------------------------- |
| book/manga         | ISBN13      | ISBN → title + author (normalized)      |
| movie/series/anime | IMDB ID     | TMDB ID → title + year                  |
| music              | Discogs ID  | UPC-EAN13 → artist + title (normalized) |

---

## Rating System

- **Scale:** 1–5 stars (integers only)
- **NULL** = unrated (never store 0)
- **Source ratings** are imported and converted to 1–5
- **User ratings** set via the app UI override imported ratings
- **Rating history** is tracked in a separate `rating_events` table (audit trail)

---

## Gold Layer Schema

### `gold_unified_tastes`

```sql
id                VARCHAR PRIMARY KEY,  -- SHA256(domain + source + source_id)
domain            VARCHAR NOT NULL,     -- music|book|manga|movie|series|anime
source            VARCHAR NOT NULL,     -- musicbuddy|spotify|bookbuddy|goodreads|moviebuddy|letterboxd|trakt
source_id         VARCHAR,             -- original ID in source system
title             VARCHAR NOT NULL,
creator           VARCHAR,             -- artist / author / director
year              INTEGER,
genres            VARCHAR[],           -- normalized array
cover_url         VARCHAR,
external_ids      JSON,                -- {imdb, tmdb, isbn13, discogs_id, spotify_id, trakt_id}
status            VARCHAR,             -- owned|watched|read|wishlist|previously_owned|unread
date_added        TIMESTAMP,
date_consumed     TIMESTAMP,          -- date read/watched/listened
created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### `gold_ratings`

```sql
id                VARCHAR PRIMARY KEY,
item_id           VARCHAR REFERENCES gold_unified_tastes(id),
rating            INTEGER CHECK (rating BETWEEN 1 AND 5),
source            VARCHAR,             -- imported|user
rated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
notes             VARCHAR
```

### `gold_rating_events` (audit trail)

```sql
id                VARCHAR PRIMARY KEY,
item_id           VARCHAR,
old_rating        INTEGER,
new_rating        INTEGER,
changed_by        VARCHAR DEFAULT 'user',
changed_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

---

## Tech Stack

| Layer            | Technology              | Version |
| ---------------- | ----------------------- | ------- |
| Language         | Python                  | 3.11+   |
| Warehouse        | DuckDB                  | latest  |
| Transformation   | dbt-duckdb              | latest  |
| API framework    | FastAPI                 | latest  |
| Agent framework  | LangGraph               | latest  |
| Chat UI          | Chainlit                | latest  |
| Dashboard        | Evidence.dev            | latest  |
| Containerization | Docker + docker-compose | —       |
| Deployment       | Coolify on Hetzner VPS  | —       |
| i18n             | FR (default) / EN       | —       |

---

## Project Structure

```
tastebase/
├── .env.example                  # Environment variables template (never commit .env)
├── .gitignore
├── README.md
├── CONTEXT.md                    # This file
├── Makefile                      # Developer commands
├── docker-compose.yml
├── Dockerfile
│
├── data/
│   ├── raw/                      # User CSV exports (gitignored)
│   │   ├── musicbuddy.csv
│   │   ├── bookbuddy.csv
│   │   ├── goodreads.csv
│   │   ├── moviebuddy.csv
│   │   └── letterboxd.csv
│   ├── templates/                # CSV templates for users without Buddy+/Goodreads/Letterboxd
│   │   ├── template_music.csv
│   │   ├── template_books.csv
│   │   ├── template_manga.csv
│   │   ├── template_movies.csv
│   │   ├── template_series.csv
│   │   └── template_anime.csv
│   └── warehouse.duckdb          # Generated database (gitignored)
│
├── ingestion/
│   ├── __init__.py
│   ├── base_loader.py            # Abstract base class for all loaders
│   ├── csv/
│   │   ├── __init__.py
│   │   ├── musicbuddy_loader.py
│   │   ├── bookbuddy_loader.py
│   │   ├── goodreads_loader.py
│   │   ├── moviebuddy_loader.py
│   │   ├── letterboxd_loader.py
│   │   └── generic_loader.py     # Handles user-supplied template CSVs
│   ├── apis/
│   │   ├── __init__.py
│   │   ├── spotify_client.py
│   │   └── trakt_client.py
│   └── run_ingestion.py          # Orchestrator: runs all loaders
│
├── transform/                    # dbt project
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── bronze/
│   │   │   ├── bronze_musicbuddy.sql
│   │   │   ├── bronze_bookbuddy.sql
│   │   │   ├── bronze_goodreads.sql
│   │   │   ├── bronze_moviebuddy.sql
│   │   │   ├── bronze_letterboxd.sql
│   │   │   ├── bronze_spotify.sql
│   │   │   └── bronze_trakt.sql
│   │   ├── silver/
│   │   │   ├── silver_music.sql
│   │   │   ├── silver_books.sql      # includes manga detection
│   │   │   ├── silver_movies.sql     # includes anime detection
│   │   │   └── silver_series.sql     # excludes anime
│   │   └── gold/
│   │       ├── gold_unified_tastes.sql
│   │       ├── gold_ratings.sql
│   │       ├── gold_rating_events.sql
│   │       ├── gold_top_rated.sql
│   │       └── gold_taste_profile.sql
│   └── seeds/
│       ├── manga_publishers.csv      # Known manga publishers for detection
│       └── domain_mapping.csv        # Category → domain override map
│
├── agent/
│   ├── __init__.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── sql_tool.py               # Natural language → DuckDB SQL
│   │   ├── rating_tool.py            # Add/update ratings
│   │   └── recommend_tool.py         # Cross-domain recommendations
│   ├── graph.py                      # LangGraph agent definition
│   ├── prompts.py                    # System prompts (FR/EN)
│   └── app.py                        # Chainlit app entry point
│
├── api/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app
│   ├── routers/
│   │   ├── items.py                  # CRUD for taste items
│   │   ├── ratings.py                # Rating endpoints
│   │   ├── ingestion.py              # Trigger re-ingestion via UI
│   │   └── stats.py                  # Dashboard data
│   └── schemas/
│       ├── item.py
│       └── rating.py
│
├── frontend/                         # Responsive web UI
│   ├── index.html
│   ├── assets/
│   │   ├── css/
│   │   └── js/
│   └── i18n/
│       ├── fr.json                   # French translations (default)
│       └── en.json                   # English translations
│
└── docs/
    ├── data-sources.md               # How to export from each supported app
    ├── csv-templates.md              # Documentation for custom CSV templates
    ├── deployment.md                 # Coolify + Hetzner setup guide
    └── contributing.md
```

---

## CSV Templates (for users without Buddy+/Goodreads/Letterboxd)

Standard column set for each domain. All templates share these common columns:

```
title, creator, year, genres, rating (1-5), status, date_added, notes
```

Domain-specific additions:

| Domain | Extra columns                                |
| ------ | -------------------------------------------- |
| music  | artist, album_type (album/single/ep), label  |
| book   | isbn, publisher, pages, language             |
| manga  | isbn, publisher, volume, language            |
| movie  | director, imdb_id, runtime_minutes, language |
| series | network, seasons, imdb_id, language          |
| anime  | studio, episodes, mal_id, language           |

---

## Coding Conventions

- **Language:** All code, comments, variable names, function names in **English**
- **Style:** PEP 8 for Python, with type hints on all functions
- **Documentation:** Docstrings on all classes and public functions
- **Comments:** Inline comments for non-obvious logic
- **Tests:** pytest for ingestion and transformation logic
- **Secrets:** Never committed — use `.env` + `python-dotenv`
- **Logging:** `logging` module, never `print()` in production code

---

## Environment Variables

```bash
# .env.example

# Spotify API
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

# Trakt.tv API
TRAKT_CLIENT_ID=
TRAKT_CLIENT_SECRET=
TRAKT_ACCESS_TOKEN=

# App
APP_SECRET_KEY=
APP_ENV=development        # development | production
DEFAULT_LANGUAGE=fr        # fr | en

# Database
DUCKDB_PATH=data/warehouse.duckdb
```

---

## Developer Commands (Makefile)

```bash
make install          # Install Python dependencies
make ingest           # Run all ingestion scripts
make transform        # Run dbt models (bronze → silver → gold)
make pipeline         # ingest + transform (full refresh)
make api              # Start FastAPI backend (port 8000)
make agent            # Start Chainlit agent UI (port 8080)
make frontend         # Start Vue frontend dev server (port 5173)
make dashboard-sync   # Copy warehouse.duckdb to Evidence source folder
make dashboard        # Sync warehouse + start Evidence dev server (port 3000)
make stack            # Start API + agent + frontend in parallel
make dev-all          # Start everything: API + agent + frontend + dashboard
make dev              # Start full stack via Docker Compose (production-like)
make test             # Run pytest
make lint             # Run ruff + mypy
```

---

## Deployment

The app runs as Docker containers on a Hetzner VPS managed by Coolify.

**Services:**

- `api`: FastAPI backend (port 8000)
- `agent`: Chainlit chat interface (port 8080)
- `dashboard`: Evidence.dev (port 3000)

**Data persistence:** DuckDB file mounted as a Docker volume.

**Update workflow:**

1. User exports new CSV from Buddy+/Goodreads/Letterboxd
2. Uploads CSV via the web UI (drag & drop)
3. App triggers `run_ingestion.py` + `dbt run` in the background
4. Gold layer refreshes automatically
5. Agent and dashboard reflect updated data

---

## i18n Strategy

- Default language: **French (FR)**
- Supported: French, English
- Translation files: `frontend/i18n/fr.json` and `frontend/i18n/en.json`
- Agent prompts: available in both languages (`agent/prompts.py`)
- Language toggle: persistent via localStorage / user preference

---

## Key Design Decisions

1. **DuckDB over PostgreSQL** — zero-infra, single file, sufficient for personal data volume, portable
2. **dbt-duckdb over raw SQL** — lineage, testing, documentation, modular transformations
3. **LangGraph over CrewAI** — fine-grained control over agent state, better for structured SQL queries
4. **Chainlit for agent UI** — purpose-built for conversational AI, easier than building custom chat UI
5. **Evidence.dev for dashboard** — markdown + SQL, dbt-native, generates static sites
6. **CSV templates** — makes the app usable by anyone, not just Buddy+/Goodreads/Letterboxd users
7. **Dedup at silver layer** — keeps bronze as immutable raw data, deduplication logic in version-controlled SQL

---

## Blog Series (Web2Data)

This project will be documented in a multi-part series:

1. Architecture overview — why a personal data warehouse?
2. Ingestion — normalizing heterogeneous CSV sources
3. dbt medallion architecture on personal data
4. Deduplication strategies in SQL
5. Building a LangGraph agent on top of DuckDB
6. Deploying on Coolify + Hetzner
7. Making it open source and multilingual

---

## References

- [dbt-duckdb docs](https://github.com/duckdb/dbt-duckdb)
- [LangGraph docs](https://langchain-ai.github.io/langgraph/)
- [Chainlit docs](https://docs.chainlit.io)
- [Evidence.dev docs](https://docs.evidence.dev)
- [Trakt.tv API](https://trakt.docs.apiary.io)
- [Spotify Web API](https://developer.spotify.com/documentation/web-api)
