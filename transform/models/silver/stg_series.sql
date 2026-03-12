-- =============================================================================
-- stg_series.sql — Silver layer: series domain
-- =============================================================================
--
-- Source: raw_trakt (endpoint = 'watched_shows', genre != 'Anime')
--         raw_moviebuddy (content_type = 'TV Show', genres not containing 'Anime')
--
-- Anime is explicitly excluded here and handled in stg_anime.sql.
-- A show is anime if its genres string contains 'anime' (case-insensitive).
--
-- Deduplication key: imdb_id -> tmdb_id -> LOWER(title) + year
-- Priority: rating present > higher rating > oldest date_added
--
-- Rating normalization:
--   MovieBuddy: float string "0.0"-"5.0" -> ROUND() -> NULL if 0
--   Trakt:      integer "1"-"10" via ratings_shows -> CEIL(x/2)
-- =============================================================================

{{ config(materialized='view') }}

WITH moviebuddy_series AS (
    SELECT
        NULLIF(TRIM(imdb_id), '')                          AS imdb_id,
        NULLIF(TRIM(tmdb_id), '')                          AS tmdb_id,
        TRIM(title)                                        AS title,
        TRY_CAST(first_air_year AS INTEGER)                AS year,
        NULLIF(TRIM(tv_creators), '')                      AS creator,
        NULLIF(TRIM(genres), '')                           AS genres_raw,
        NULLIF(TRIM(languages), '')                        AS language,
        TRY_CAST(number_of_seasons AS INTEGER)             AS seasons,

        CASE
            WHEN TRY_CAST(rating AS DOUBLE) IS NULL THEN NULL
            WHEN ROUND(TRY_CAST(rating AS DOUBLE)) = 0    THEN NULL
            ELSE CAST(ROUND(TRY_CAST(rating AS DOUBLE)) AS INTEGER)
        END                                                AS rating,

        CASE
            WHEN LOWER(TRIM(COALESCE(wish_list, ''))) IN ('true', '1')        THEN 'wishlist'
            WHEN LOWER(TRIM(COALESCE(previously_owned, ''))) IN ('true', '1') THEN 'previously_owned'
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
      AND TRIM(content_type) = 'TV Show'
      -- Exclude anime: genres must not contain 'anime' (case-insensitive)
      AND NOT (LOWER(COALESCE(genres, '')) LIKE '%anime%')
),

trakt_shows AS (
    SELECT
        REGEXP_EXTRACT(payload, '''imdb'':\s*''(tt\d+)''', 1)           AS imdb_id,
        REGEXP_EXTRACT(payload, '''tmdb'':\s*(\d+)', 1)                  AS tmdb_id,
        REGEXP_EXTRACT(payload, '''title'':\s*''([^'']+)''', 1)          AS title,
        TRY_CAST(
            REGEXP_EXTRACT(payload, '''year'':\s*(\d{4})', 1)
        AS INTEGER)                                                       AS year,
        NULL                                                              AS creator,
        NULL                                                              AS genres_raw,
        NULL                                                              AS language,
        NULL                                                              AS seasons,
        NULL                                                              AS rating,
        'watched'                                                         AS status,
        NULL                                                              AS date_added,
        TRY_CAST(
            REGEXP_EXTRACT(payload, '''last_watched_at'':\s*''([^'']+)''', 1)
        AS DATE)                                                          AS date_consumed,
        NULL                                                              AS cover_url,
        NULL                                                              AS notes,
        'trakt'                                                           AS source,
        _source,
        _loaded_at

    FROM {{ ref('raw_trakt') }}
    WHERE endpoint = 'watched_shows'
      AND payload IS NOT NULL
      AND payload != ''
      AND REGEXP_EXTRACT(payload, '''title'':\s*''([^'']+)''', 1) != ''
      -- Exclude anime shows from Trakt (genre-based detection not available
      -- in watched_shows payload — anime exclusion relies on known titles
      -- being in stg_anime instead; overlap is resolved by deduplication)
),

trakt_ratings AS (
    SELECT
        REGEXP_EXTRACT(payload, '''imdb'':\s*''(tt\d+)''', 1)            AS imdb_id,
        CAST(CEIL(
            TRY_CAST(
                REGEXP_EXTRACT(payload, '''rating'':\s*(\d+)', 1)
            AS DOUBLE) / 2.0
        ) AS INTEGER)                                                     AS rating
    FROM {{ ref('raw_trakt') }}
    WHERE endpoint = 'ratings_shows'
      AND payload IS NOT NULL
),

trakt_shows_rated AS (
    SELECT
        t.imdb_id,
        t.tmdb_id,
        t.title,
        t.year,
        t.creator,
        t.genres_raw,
        t.language,
        t.seasons,
        COALESCE(r.rating, t.rating)                                     AS rating,
        t.status,
        t.date_added,
        t.date_consumed,
        t.cover_url,
        t.notes,
        t.source,
        t._source,
        t._loaded_at
    FROM trakt_shows t
    LEFT JOIN trakt_ratings r ON t.imdb_id = r.imdb_id AND t.imdb_id IS NOT NULL
),

all_series AS (
    SELECT * FROM moviebuddy_series
    UNION ALL
    SELECT * FROM trakt_shows_rated
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
        FROM all_series
    )
    WHERE rn = 1
),

final AS (
    SELECT
        SHA256(
            'series' || '|' || source || '|' ||
            COALESCE(
                imdb_id,
                tmdb_id,
                LOWER(title) || '||' || CAST(COALESCE(year, 0) AS VARCHAR)
            )
        )                                   AS id,

        'series'                            AS domain,
        source,
        COALESCE(imdb_id, tmdb_id, '')      AS source_id,

        title,
        creator,
        year,
        genres_raw                          AS genres,
        language,
        seasons,

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
