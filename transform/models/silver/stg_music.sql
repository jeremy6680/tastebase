-- =============================================================================
-- stg_music.sql — Silver layer: music domain
-- =============================================================================
--
-- Sources:
--   - raw_musicbuddy (PRIMARY — carries ratings, Discogs metadata)
--   - raw_spotify    (ENRICHMENT ONLY — cover art and spotify_id)
--
-- Deduplication key: discogs_release_id -> upc_ean13 -> artist + title
--
-- Rating normalization (applied here, never in bronze):
--   MusicBuddy float string "0.000000"-"5.000000" -> ROUND() -> NULL if 0
--
-- Spotify has no native rating and is never used as a rating source.
-- raw_spotify may be empty when Spotify is rate-limited. The LEFT JOIN
-- handles this gracefully: MusicBuddy rows are always returned, Spotify
-- enrichment columns are NULL when no match is found.
-- =============================================================================

{{ config(materialized='view') }}

WITH musicbuddy_normalized AS (
    SELECT
        NULLIF(TRIM(discogs_release_id), '')    AS discogs_release_id,
        NULLIF(TRIM(upc_ean13), '')             AS upc_ean13,
        TRIM(title)                             AS title,
        TRIM(artist)                            AS artist,
        TRY_CAST(release_year AS INTEGER)       AS year,
        TRIM(country)                           AS country,
        TRIM(language)                          AS language,
        NULLIF(TRIM(genres), '')                AS genres_raw,
        NULLIF(TRIM(styles), '')                AS styles_raw,
        NULLIF(TRIM(media), '')                 AS media,
        NULLIF(TRIM(format), '')                AS format,

        CASE
            WHEN TRY_CAST(rating AS DOUBLE) IS NULL THEN NULL
            WHEN ROUND(TRY_CAST(rating AS DOUBLE)) = 0 THEN NULL
            ELSE CAST(ROUND(TRY_CAST(rating AS DOUBLE)) AS INTEGER)
        END                                     AS rating,

        CASE
            -- MusicBuddy exports booleans as "true"/"false" strings or "1"/"0"
            WHEN LOWER(TRIM(wish_list)) IN ('true', '1')        THEN 'wishlist'
            WHEN LOWER(TRIM(previously_owned)) IN ('true', '1') THEN 'previously_owned'
            ELSE 'owned'
        END                                     AS status,

        TRY_CAST(date_added AS DATE)            AS date_added,
        TRY_CAST(purchase_date AS DATE)         AS date_consumed,
        NULLIF(TRIM(cover_url), '')             AS cover_url,
        NULLIF(TRIM(labels), '')                AS labels,
        NULLIF(TRIM(tags), '')                  AS tags,
        NULLIF(TRIM(notes), '')                 AS notes,
        _source,
        _loaded_at

    FROM {{ ref('raw_musicbuddy') }}
    WHERE TRIM(title) != ''
      AND TRIM(artist) != ''
),

musicbuddy_deduped AS (
    SELECT *
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY
                    COALESCE(
                        discogs_release_id,
                        upc_ean13,
                        LOWER(TRIM(artist)) || '||' || LOWER(TRIM(title))
                    )
                ORDER BY
                    CASE WHEN rating IS NOT NULL THEN 0 ELSE 1 END ASC,
                    COALESCE(rating, 0) DESC,
                    date_added ASC
            ) AS rn
        FROM musicbuddy_normalized
    )
    WHERE rn = 1
),

-- Spotify enrichment: extract fields from Python repr payload strings.
-- raw_spotify is empty when Spotify is rate-limited — the LEFT JOIN below
-- handles that case and simply returns NULL for all Spotify columns.
-- When Spotify ingestion is healthy, this CTE returns one row per saved album.
spotify_albums AS (
    SELECT
        REGEXP_EXTRACT(payload, '''id'':\s*''([A-Za-z0-9]+)''', 1)                AS spotify_id,
        REGEXP_EXTRACT(payload, '''name'':\s*''([^'']+)''', 1)                     AS title_raw,
        REGEXP_EXTRACT(payload, '''url'':\s*''(https://i\.scdn\.co/[^'']+)''', 1) AS spotify_cover_url
    FROM {{ ref('raw_spotify') }}
    WHERE endpoint = 'saved_albums'
      AND payload IS NOT NULL
      AND payload != ''
),

final AS (
    SELECT
        SHA256(
            'music' || '|' || 'musicbuddy' || '|' ||
            COALESCE(
                mb.discogs_release_id,
                mb.upc_ean13,
                LOWER(mb.artist) || '||' || LOWER(mb.title)
            )
        )                                       AS id,

        'music'                                 AS domain,
        'musicbuddy'                            AS source,
        COALESCE(mb.discogs_release_id, '')     AS source_id,

        mb.title,
        mb.artist                               AS creator,
        mb.year,
        mb.genres_raw                           AS genres,
        mb.styles_raw                           AS styles,
        mb.media,
        mb.format,
        mb.country,
        mb.language,
        mb.rating,
        mb.status,
        mb.date_added,
        mb.date_consumed,

        -- Cover: prefer MusicBuddy (Discogs), fall back to Spotify
        COALESCE(mb.cover_url, sp.spotify_cover_url) AS cover_url,

        mb.discogs_release_id,
        mb.upc_ean13,
        sp.spotify_id,

        mb.labels,
        mb.tags,
        mb.notes,
        mb._source,
        mb._loaded_at

    FROM musicbuddy_deduped mb
    LEFT JOIN spotify_albums sp
        ON LOWER(TRIM(mb.title)) = LOWER(TRIM(sp.title_raw))
)

SELECT * FROM final
