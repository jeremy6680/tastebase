# Data sources — TasteBase

> Step-by-step instructions for exporting your data from each supported app.
> After exporting, see the [README](../README.md) for how to import files into TasteBase.

---

## Supported sources

| App                       | Domain(s)             | Export type | Required?                          |
| ------------------------- | --------------------- | ----------- | ---------------------------------- |
| [MusicBuddy](#musicbuddy) | Music                 | CSV         | Recommended                        |
| [BookBuddy](#bookbuddy)   | Books, Manga          | CSV         | Recommended                        |
| [Goodreads](#goodreads)   | Books, Manga          | CSV         | Optional (enriches BookBuddy)      |
| [MovieBuddy](#moviebuddy) | Movies, Series, Anime | CSV         | Recommended                        |
| [Letterboxd](#letterboxd) | Movies                | CSV         | Optional (enriches MovieBuddy)     |
| [Spotify](#spotify)       | Music                 | API         | Optional (cover art enrichment)    |
| [Trakt.tv](#trakt)        | Movies, Series        | API         | Optional (watch history + ratings) |

You do not need all sources. TasteBase will simply skip any source with no file present
in `data/raw/`.

---

## MusicBuddy

**Domains:** Music  
**Canonical filename:** `data/raw/musicbuddy.csv`  
**Role:** Primary music source. MusicBuddy ratings take precedence over Spotify.

### Export steps

1. Open the **MusicBuddy** app on iOS or Android
2. Tap **Settings** (gear icon, bottom right)
3. Tap **Export data**
4. Select **CSV** as the format
5. Share or save the file — it will be named something like `MusicBuddy 2026-03-05 144228.csv`

### Rename the file

```bash
cp ~/Downloads/MusicBuddy*.csv /path/to/tastebase/data/raw/musicbuddy.csv
```

### Key columns used by TasteBase

| Column   | Description                                    |
| -------- | ---------------------------------------------- |
| `title`  | Album title                                    |
| `artist` | Artist name                                    |
| `year`   | Release year                                   |
| `rating` | User rating (0.0–5.0 float)                    |
| `status` | Listening status (e.g. "Listened", "Wishlist") |
| `genres` | Comma-separated genre list                     |

---

## BookBuddy

**Domains:** Books, Manga  
**Canonical filename:** `data/raw/bookbuddy.csv`  
**Role:** Primary book and manga source.

### Export steps

1. Open the **BookBuddy** app on iOS or Android
2. Tap **Settings** → **Export**
3. Select **CSV**
4. Save or share the exported file

### Rename the file

```bash
cp ~/Downloads/BookBuddy*.csv /path/to/tastebase/data/raw/bookbuddy.csv
```

### Manga detection

TasteBase identifies manga entries in BookBuddy by cross-referencing the publisher
against a known list (`transform/seeds/manga_publishers.csv` — includes Viz Media,
Kodansha, Shueisha, Shogakukan, etc.) and by scanning the title for common manga
keywords. Entries that match are assigned `domain = 'manga'`; all others become books.

### Key columns used by TasteBase

| Column      | Description                                        |
| ----------- | -------------------------------------------------- |
| `title`     | Book/manga title                                   |
| `author`    | Author name                                        |
| `isbn13`    | ISBN-13 (used as deduplication key with Goodreads) |
| `rating`    | User rating (0.0–5.0 float)                        |
| `status`    | Reading status                                     |
| `publisher` | Publisher name (used for manga detection)          |

---

## Goodreads

**Domains:** Books, Manga  
**Canonical filename:** `data/raw/goodreads.csv`  
**Role:** Optional enrichment for BookBuddy. Fills in missing ratings and metadata.

### Export steps

1. Go to [goodreads.com](https://www.goodreads.com) and sign in
2. Click your profile picture → **My Books**
3. Click **Import and export** (bottom of the left sidebar)
4. Click **Export Library**
5. Wait for the export to prepare, then click the download link
6. The file is named `goodreads_library_export.csv`

### Rename the file

```bash
cp ~/Downloads/goodreads_library_export.csv /path/to/tastebase/data/raw/goodreads.csv
```

### Key columns used by TasteBase

| Column            | Description                                |
| ----------------- | ------------------------------------------ |
| `Title`           | Book title                                 |
| `Author`          | Author name                                |
| `ISBN13`          | ISBN-13 (deduplication key with BookBuddy) |
| `My Rating`       | User rating (integer 0–5)                  |
| `Exclusive Shelf` | Shelf name (used for status detection)     |

---

## MovieBuddy

**Domains:** Movies, Series, Anime  
**Canonical filename:** `data/raw/moviebuddy.csv`  
**Role:** Primary movie, series, and anime source.

### Export steps

1. Open the **MovieBuddy** app on iOS or Android
2. Tap **Settings** → **Export**
3. Select **CSV**
4. Save or share the exported file

### Rename the file

```bash
cp ~/Downloads/MovieBuddy*.csv /path/to/tastebase/data/raw/moviebuddy.csv
```

### Domain detection

MovieBuddy exports all items together. TasteBase splits them at the silver layer:

- **Movies:** `type = 'Movie'`
- **Series:** `type = 'TV Show'` and genres do not contain "Anime"
- **Anime:** `type = 'TV Show'` and genres contain "Anime"

> ⚠️ **Known limitation:** MovieBuddy uses TMDB genre data, which labels animated content
> as "Animation" — not "Anime". As a result, `stg_anime` returns 0 rows for most users.
> This is a known gap (DEC-019) tracked in the backlog.

### Key columns used by TasteBase

| Column     | Description                            |
| ---------- | -------------------------------------- |
| `title`    | Movie/show title                       |
| `director` | Director name (movies)                 |
| `year`     | Release year                           |
| `rating`   | User rating (0.0–5.0 float)            |
| `type`     | "Movie" or "TV Show"                   |
| `genres`   | Comma-separated genre list (from TMDB) |
| `tmdb_id`  | TMDB ID (deduplication key)            |

---

## Letterboxd

**Domains:** Movies  
**Canonical filename:** `data/raw/letterboxd.csv`  
**Role:** Optional enrichment for MovieBuddy. Adds Letterboxd ratings and watch dates.

### Export steps

1. Go to [letterboxd.com](https://letterboxd.com) and sign in
2. Click your profile picture → **Settings**
3. Scroll down to **Data** → click **Export your data**
4. A `.zip` archive is emailed to you (usually within a few minutes)
5. Unzip the archive — you'll find several CSV files including `ratings.csv`

> TasteBase uses the `ratings.csv` file from the Letterboxd export archive.

### Rename the file

```bash
# After unzipping the Letterboxd export:
cp ~/Downloads/letterboxd-*/ratings.csv /path/to/tastebase/data/raw/letterboxd.csv
```

### Key columns used by TasteBase

| Column           | Description                             |
| ---------------- | --------------------------------------- |
| `Name`           | Film title                              |
| `Year`           | Release year                            |
| `Rating`         | User rating (0.5–5.0 in 0.5 increments) |
| `Letterboxd URI` | Letterboxd URL (used as secondary ID)   |
| `Watched Date`   | Date watched                            |

---

## Spotify

**Domains:** Music  
**Connection type:** OAuth API  
**Role:** Optional enrichment only — provides cover art and Spotify IDs for MusicBuddy entries.
Spotify does not contain user ratings.

### Setup

Spotify requires an OAuth access token. You need to create an app in the Spotify
Developer Dashboard:

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Click **Create app**
3. Set the redirect URI to `http://localhost:8888/callback`
4. Note your **Client ID** and **Client Secret**
5. Run the OAuth flow to obtain an access token and refresh token (see below)

### Obtain tokens

TasteBase does not include an OAuth UI. Use the
[Spotify OAuth helper](https://github.com/spotify/web-api-examples) or any OAuth
tool (e.g. `spotipy`) to complete the authorization code flow and retrieve:

- `SPOTIFY_ACCESS_TOKEN`
- `SPOTIFY_REFRESH_TOKEN`

### Configure `.env`

```bash
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_ACCESS_TOKEN=your_access_token
SPOTIFY_REFRESH_TOKEN=your_refresh_token
```

### Rate limiting

Spotify enforces extended rate limits (up to ~23 hours). When rate-limited, TasteBase
skips Spotify ingestion automatically and logs a warning. All other sources are unaffected.
Spotify enrichment in `stg_music` uses a `LEFT JOIN` — MusicBuddy entries are never
dropped if Spotify data is missing.

---

## Trakt.tv

**Domains:** Movies, Series  
**Connection type:** OAuth API  
**Role:** Provides watch history and ratings for movies and TV shows.

### Setup

1. Go to [trakt.tv/oauth/applications](https://trakt.tv/oauth/applications)
2. Click **New application**
3. Set the redirect URI to `urn:ietf:wg:oauth:2.0:oob` (for local use)
4. Note your **Client ID** and **Client Secret**
5. Complete the OAuth flow to obtain your tokens

### Configure `.env`

```bash
TRAKT_CLIENT_ID=your_client_id
TRAKT_CLIENT_SECRET=your_client_secret
TRAKT_ACCESS_TOKEN=your_access_token
TRAKT_REFRESH_TOKEN=your_refresh_token
```

### What Trakt provides

| Data                 | Used for                          |
| -------------------- | --------------------------------- |
| Watched movies       | Enriches `stg_movies`             |
| Watched shows        | Enriches `stg_series`             |
| Movie ratings (1–10) | Normalized to 1–5 at silver layer |
| Show ratings (1–10)  | Normalized to 1–5 at silver layer |

> Trakt ratings are normalized using `CEIL(rating / 2.0)` at the silver layer
> to align with TasteBase's unified 1–5 integer scale (DEC-004).

---

## Using CSV templates

If you don't use any of the supported apps, TasteBase provides CSV templates for
each domain that you can fill in manually:

| Domain | Template                             |
| ------ | ------------------------------------ |
| Music  | `data/templates/template_music.csv`  |
| Books  | `data/templates/template_books.csv`  |
| Manga  | `data/templates/template_manga.csv`  |
| Movies | `data/templates/template_movies.csv` |
| Series | `data/templates/template_series.csv` |
| Anime  | `data/templates/template_anime.csv`  |

See [`docs/csv-templates.md`](csv-templates.md) for the full column reference.
