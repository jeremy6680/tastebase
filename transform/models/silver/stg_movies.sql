-- =============================================================================
-- stg_movies.sql — Silver layer: movie domain
-- =============================================================================
--
-- Sources:
--   - raw_moviebuddy  (PRIMARY for movies — content_type = 'Movie')
--   - raw_letterboxd  (SECONDARY — merged via title + release_year)
--   - raw_trakt       (SECONDARY — endpoint = 'watched_movies')
--
-- Domain: all rows here are 'movie'. Anime and series are handled in
-- their own models (stg_anime.sql, stg_series.sql).
--
-- Deduplication key: imdb_id -> tmdb_id -> LOWER(title) + release_year
-- Priority: rating present > higher rating > oldest date_added
--
-- Rating normalization:
--   MovieBuddy: float string "0.0"-"5.0" -> ROUND() -> NULL if 0
--   Letterboxd: float string "0.5"-"5.0" -> ROUND() -> NULL if 0
--   Trakt:      integer string "1"-"10"  -> CEIL(x/2) -> NULL if missing
--
-- Trakt payloads are stored as Python repr strings (str(dict)).
-- Fields are extracted via REGEXP_EXTRACT as best-effort parsing.
-- =============================================================================

{{ config(materialized='view') }}

WITH moviebuddy_movies AS (
    SELECT
        NULLIF(TRIM(imdb_id), '')                          AS imdb_id,
        NULLIF(TRIM(tmdb_id), '')                          AS tmdb_id,
        TRIM(title)                                        AS title,
        TRY_CAST(release_year AS INTEGER)                  AS year,
        NULLIF(TRIM(directors), '')                        AS creator,
        NULLIF(TRIM(genres), '')                           AS genres_raw,
        NULLIF(TRIM(languages), '')                        AS language,

        CASE
            WHEN TRY_CAST(rating AS DOUBLE) IS NULL THEN NULL
            WHEN ROUND(TRY_CAST(rating AS DOUBLE)) = 0    THEN NULL
            ELSE CAST(ROUND(TRY_CAST(rating AS DOUBLE)) AS INTEGER)
        END                                                AS rating,

        CASE
            WHEN LOWER(TRIM(COALESCE(wish_list, ''))) IN ('true', '1')        THEN 'wishlist'
            WHEN LOWER(TRIM(COALESCE(previously_owned, ''))) IN ('true', '1') THEN 'previously_owned'
            WHEN LOWER(TRIM(COALESCE(status, ''))) = 'watched'                THEN 'watched'
            ELSE 'watched'
        END                                                AS status,

        TRY_CAST(date_added AS DATE)                       AS date_added,
        TRY_CAST(date_finished AS DATE)                    AS date_consumed,
        NULLIF(TRIM(cover_url), '')                        AS cover_url,
        NULLIF(TRIM(notes), '')                            AS notes,

        'moviebuddy'                                       AS source,
        _source,
        _loaded_at

    FROM {{ ref('raw_moviebuddy') }}
    WHERE TRIM(title) != ''
      AND TRIM(content_type) = 'Movie'
),

letterboxd_movies AS (
    SELECT
        NULL                                               AS imdb_id,
        NULL                                               AS tmdb_id,
        TRIM(title)                                        AS title,
        TRY_CAST(release_year AS INTEGER)                  AS year,
        NULL                                               AS creator,
        NULL                                               AS genres_raw,
        NULL                                               AS language,

        -- Letterboxd: 0.5-5.0 in 0.5 increments -> round to nearest integer
        CASE
            WHEN TRY_CAST(rating AS DOUBLE) IS NULL THEN NULL
            WHEN ROUND(TRY_CAST(rating AS DOUBLE)) = 0    THEN NULL
            ELSE CAST(ROUND(TRY_CAST(rating AS DOUBLE)) AS INTEGER)
        END                                                AS rating,

        'watched'                                          AS status,
        TRY_CAST(date_added AS DATE)                       AS date_added,
        TRY_CAST(date_added AS DATE)                       AS date_consumed,
        NULL                                               AS cover_url,
        NULL                                               AS notes,

        'letterboxd'                                       AS source,
        _source,
        _loaded_at

    FROM {{ ref('raw_letterboxd') }}
    WHERE TRIM(title) != ''
),

-- Extract movie fields from Trakt Python repr payload strings.
-- Trakt stores nested dicts as str(dict) — we use REGEXP_EXTRACT
-- to pull scalar fields. Complex nested fields are skipped.
trakt_movies AS (
    SELECT
        REGEXP_EXTRACT(payload, '''imdb'':\s*''(tt\d+)''', 1)          AS imdb_id,
        REGEXP_EXTRACT(payload, '''tmdb'':\s*(\d+)', 1)                 AS tmdb_id,
        REGEXP_EXTRACT(payload, '''title'':\s*''([^'']+)''', 1)         AS title,
        TRY_CAST(
            REGEXP_EXTRACT(payload, '''year'':\s*(\d{4})', 1)
        AS INTEGER)                                                      AS year,
        NULL                                                             AS creator,
        NULL                                                             AS genres_raw,
        NULL                                                             AS language,
        NULL                                                             AS rating,
        'watched'                                                        AS status,
        NULL                                                             AS date_added,
        TRY_CAST(
            REGEXP_EXTRACT(payload, '''last_watched_at'':\s*''([^'']+)''', 1)
        AS DATE)                                                         AS date_consumed,
        NULL                                                             AS cover_url,
        NULL                                                             AS notes,
        'trakt'                                                          AS source,
        _source,
        _loaded_at

    FROM {{ ref('raw_trakt') }}
    WHERE endpoint = 'watched_movies'
      AND payload IS NOT NULL
      AND payload != ''
      -- Only keep rows where we extracted a title
      AND REGEXP_EXTRACT(payload, '''title'':\s*''([^'']+)''', 1) != ''
),

-- Apply Trakt ratings from the ratings_movies endpoint
-- Join ratings onto watched_movies via imdb_id
trakt_ratings AS (
    SELECT
        REGEXP_EXTRACT(payload, '''imdb'':\s*''(tt\d+)''', 1)           AS imdb_id,
        CAST(CEIL(
            TRY_CAST(
                REGEXP_EXTRACT(payload, '''rating'':\s*(\d+)', 1)
            AS DOUBLE) / 2.0
        ) AS INTEGER)                                                    AS rating
    FROM {{ ref('raw_trakt') }}
    WHERE endpoint = 'ratings_movies'
      AND payload IS NOT NULL
),

trakt_movies_rated AS (
    SELECT
        t.imdb_id,
        t.tmdb_id,
        t.title,
        t.year,
        t.creator,
        t.genres_raw,
        t.language,
        COALESCE(r.rating, t.rating)                                    AS rating,
        t.status,
        t.date_added,
        t.date_consumed,
        t.cover_url,
        t.notes,
        t.source,
        t._source,
        t._loaded_at
    FROM trakt_movies t
    LEFT JOIN trakt_ratings r ON t.imdb_id = r.imdb_id AND t.imdb_id IS NOT NULL
),

all_movies AS (
    SELECT * FROM moviebuddy_movies
    UNION ALL
    SELECT * FROM letterboxd_movies
    UNION ALL
    SELECT * FROM trakt_movies_rated
),

deduped AS (
    SELECT *
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY
                    COALESCE(
                        imdb_id,
                        tmdb_id,
                        LOWER(TRIM(title)) || '||' || CAST(COALESCE(year, 0) AS VARCHAR)
                    )
                ORDER BY
                    CASE WHEN rating IS NOT NULL THEN 0 ELSE 1 END ASC,
                    COALESCE(rating, 0) DESC,
                    date_added ASC NULLS LAST
            ) AS rn
        FROM all_movies
    )
    WHERE rn = 1
),

final AS (
    SELECT
        SHA256(
            'movie' || '|' || source || '|' ||
            COALESCE(
                imdb_id,
                tmdb_id,
                LOWER(title) || '||' || CAST(COALESCE(year, 0) AS VARCHAR)
            )
        )                                   AS id,

        'movie'                             AS domain,
        source,
        COALESCE(imdb_id, tmdb_id, '')      AS source_id,

        title,
        creator,
        year,
        genres_raw                          AS genres,
        language,

        rating,
        status,
        date_added,
        date_consumed,
        cover_url,

        imdb_id,
        tmdb_id,

        notes,
        _source,
        _loaded_at

    FROM deduped
)

SELECT * FROM final
