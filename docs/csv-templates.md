# CSV Templates — TasteBase

Use these templates if you don't have a Buddy+ account, Goodreads, or Letterboxd export.
Each template covers one content domain. Fill in your data, save the file with the
canonical filename listed below, and drop it in `data/raw/`.

---

## General rules

- **Encoding:** UTF-8
- **Delimiter:** comma (`,`)
- **Date format:** `YYYY-MM-DD`
- **Rating:** integer from 1 to 5, or leave empty if unrated
- **Genres:** comma-separated string inside double quotes if multiple values — e.g. `"Rock, Pop"`
- **Required columns:** `title`, `creator`, `year`, `status`, `date_added`
- **Optional columns:** leave empty, do not remove the column header

---

## Canonical filenames

| Domain | File to place in `data/raw/` |
| ------ | ---------------------------- |
| Music  | `data/raw/musicbuddy.csv`    |
| Books  | `data/raw/bookbuddy.csv`     |
| Manga  | `data/raw/bookbuddy.csv`     |
| Movies | `data/raw/moviebuddy.csv`    |
| Series | `data/raw/moviebuddy.csv`    |
| Anime  | `data/raw/moviebuddy.csv`    |

> **Note:** Books and manga share `bookbuddy.csv`. Movies, series, and anime share
> `moviebuddy.csv`. The loaders and silver models handle domain detection
> automatically based on genres and publishers.

---

## Allowed values

### `status`

| Value              | Meaning                          |
| ------------------ | -------------------------------- |
| `owned`            | You own it (physical or digital) |
| `read`             | Read / finished                  |
| `reading`          | Currently reading                |
| `watched`          | Watched / finished               |
| `watching`         | Currently watching               |
| `listened`         | Listened to                      |
| `wishlist`         | On your wishlist                 |
| `previously_owned` | Owned in the past, no longer     |
| `unread`           | Owned but not yet read           |

### `rating`

Integer from `1` to `5`. Leave empty if you haven't rated the item yet.
Do not use `0`.

---

## Domain templates

### Music — `data/templates/template_music.csv`

| Column       | Required | Format / Notes                      |
| ------------ | -------- | ----------------------------------- |
| `title`      | ✅       | Album title                         |
| `artist`     | ✅       | Main artist or band name            |
| `year`       | ✅       | Release year (integer)              |
| `genres`     |          | Comma-separated, quoted if multiple |
| `rating`     |          | 1–5 integer                         |
| `status`     | ✅       | See allowed values above            |
| `date_added` | ✅       | `YYYY-MM-DD`                        |
| `album_type` |          | `album`, `single`, or `ep`          |
| `label`      |          | Record label name                   |
| `notes`      |          | Free text                           |

---

### Books — `data/templates/template_books.csv`

| Column       | Required | Format / Notes                          |
| ------------ | -------- | --------------------------------------- |
| `title`      | ✅       | Book title                              |
| `creator`    | ✅       | Author name                             |
| `year`       | ✅       | Publication year (integer)              |
| `genres`     |          | Comma-separated, quoted if multiple     |
| `rating`     |          | 1–5 integer                             |
| `status`     | ✅       | See allowed values above                |
| `date_added` | ✅       | `YYYY-MM-DD`                            |
| `isbn`       |          | ISBN-13 preferred                       |
| `publisher`  |          | Publisher name                          |
| `pages`      |          | Integer                                 |
| `language`   |          | ISO 639-1 code (`en`, `fr`, `ja`, etc.) |
| `notes`      |          | Free text                               |

---

### Manga — `data/templates/template_manga.csv`

Same structure as books. The domain is detected from `publisher` (cross-referenced
against `seeds/manga_publishers.csv`) and from genre / title keywords.

| Column       | Required | Format / Notes                            |
| ------------ | -------- | ----------------------------------------- |
| `title`      | ✅       | Manga title                               |
| `creator`    | ✅       | Author / mangaka name                     |
| `year`       | ✅       | Publication year (integer)                |
| `genres`     |          | Comma-separated, quoted if multiple       |
| `rating`     |          | 1–5 integer                               |
| `status`     | ✅       | See allowed values above                  |
| `date_added` | ✅       | `YYYY-MM-DD`                              |
| `isbn`       |          | ISBN-13 of volume 1 preferred             |
| `publisher`  |          | Publisher name (used for manga detection) |
| `volume`     |          | Volume number (integer)                   |
| `language`   |          | ISO 639-1 code                            |
| `notes`      |          | Free text                                 |

---

### Movies — `data/templates/template_movies.csv`

| Column            | Required | Format / Notes                            |
| ----------------- | -------- | ----------------------------------------- |
| `title`           | ✅       | Movie title                               |
| `creator`         | ✅       | Director name (also in `director` column) |
| `year`            | ✅       | Release year (integer)                    |
| `genres`          |          | Comma-separated, quoted if multiple       |
| `rating`          |          | 1–5 integer                               |
| `status`          | ✅       | See allowed values above                  |
| `date_added`      | ✅       | `YYYY-MM-DD`                              |
| `director`        |          | Director name                             |
| `imdb_id`         |          | e.g. `tt0062622` — used for deduplication |
| `runtime_minutes` |          | Integer                                   |
| `language`        |          | ISO 639-1 code                            |
| `notes`           |          | Free text                                 |

---

### Series — `data/templates/template_series.csv`

| Column       | Required | Format / Notes                             |
| ------------ | -------- | ------------------------------------------ |
| `title`      | ✅       | Series title                               |
| `creator`    | ✅       | Creator / showrunner name                  |
| `year`       | ✅       | First air year (integer)                   |
| `genres`     |          | Comma-separated, quoted if multiple        |
| `rating`     |          | 1–5 integer                                |
| `status`     | ✅       | See allowed values above                   |
| `date_added` | ✅       | `YYYY-MM-DD`                               |
| `network`    |          | Broadcasting network or streaming platform |
| `seasons`    |          | Number of seasons (integer)                |
| `imdb_id`    |          | e.g. `tt0306414` — used for deduplication  |
| `language`   |          | ISO 639-1 code                             |
| `notes`      |          | Free text                                  |

---

### Anime — `data/templates/template_anime.csv`

| Column       | Required | Format / Notes                               |
| ------------ | -------- | -------------------------------------------- |
| `title`      | ✅       | Anime title                                  |
| `creator`    | ✅       | Director or studio name                      |
| `year`       | ✅       | First air year (integer)                     |
| `genres`     |          | Comma-separated, quoted if multiple          |
| `rating`     |          | 1–5 integer                                  |
| `status`     | ✅       | See allowed values above                     |
| `date_added` | ✅       | `YYYY-MM-DD`                                 |
| `studio`     |          | Animation studio name                        |
| `episodes`   |          | Total episode count (integer)                |
| `mal_id`     |          | MyAnimeList ID (integer) — future enrichment |
| `language`   |          | ISO 639-1 code                               |
| `notes`      |          | Free text                                    |

---

## Placing files in `data/raw/`

Books and manga go into the same file (`bookbuddy.csv`). The silver model
`stg_books.sql` detects manga entries via publisher lookup and genre keywords.

Movies, series, and anime go into `moviebuddy.csv`. The silver model
`stg_movies.sql` and `stg_anime.sql` split them based on genre signals.

If you have both a Buddy+ export **and** a custom template for the same domain,
the loaders will merge them during ingestion. Deduplication happens at the silver
layer using canonical IDs (ISBN, IMDB ID) as the primary key.
