-- =============================================================================
-- stg_books.sql — Silver layer: book and manga domains
-- =============================================================================
--
-- Sources:
--   - raw_bookbuddy  (PRIMARY for books + manga)
--   - raw_goodreads  (SECONDARY — merged via ISBN13 dedup)
--
-- Domain detection (book vs manga):
--   1. Publisher match against manga_publishers seed (strongest signal)
--   2. Category/Tags keyword match against domain_mapping seed
--   3. Bookshelves keyword match (Goodreads only)
--   4. Default: 'book'
--
-- Deduplication key: isbn13 -> isbn -> LOWER(title) + LOWER(author)
-- Priority: rating present > higher rating > oldest date_added
--
-- Rating normalization:
--   BookBuddy: float string "0.0"-"5.0" -> ROUND() -> NULL if 0
--   Goodreads:  integer string "0"-"5"   -> CAST()  -> NULL if 0
--
-- Goodreads exports ISBN values wrapped in ="..." notation (e.g. ="9780000000000").
-- The wrapper is stripped here via REGEXP_REPLACE.
-- =============================================================================

{{ config(materialized='view') }}

WITH bookbuddy_normalized AS (
    SELECT
        -- Deduplication keys
        NULLIF(TRIM(isbn), '')                              AS isbn,
        NULL                                               AS isbn13, -- BookBuddy has no ISBN13 column

        -- Identity
        TRIM(title)                                        AS title,
        TRIM(author)                                       AS author,
        TRIM(publisher)                                    AS publisher,

        -- Release info
        TRY_CAST(year_published AS INTEGER)                AS year,
        TRIM(language)                                     AS language,
        TRY_CAST(number_of_pages AS INTEGER)               AS pages,

        -- Domain detection signals
        LOWER(TRIM(COALESCE(category, '')))                AS category_lower,
        LOWER(TRIM(COALESCE(tags, '')))                    AS tags_lower,
        LOWER(TRIM(COALESCE(genre, '')))                   AS genre_lower,

        -- Rating normalization: float string -> integer 1-5, 0 -> NULL
        CASE
            WHEN TRY_CAST(rating AS DOUBLE) IS NULL THEN NULL
            WHEN ROUND(TRY_CAST(rating AS DOUBLE)) = 0    THEN NULL
            ELSE CAST(ROUND(TRY_CAST(rating AS DOUBLE)) AS INTEGER)
        END                                                AS rating,

        -- Status
        LOWER(TRIM(COALESCE(status, '')))                  AS status_raw,

        -- Dates
        TRY_CAST(date_added AS DATE)                       AS date_added,
        TRY_CAST(date_finished AS DATE)                    AS date_consumed,

        -- Enrichment
        NULLIF(TRIM(cover_url), '')                        AS cover_url,
        NULLIF(TRIM(notes), '')                            AS notes,
        NULLIF(TRIM(series), '')                           AS series,
        TRY_CAST(volume AS INTEGER)                        AS volume,

        'bookbuddy'                                        AS source,
        _source,
        _loaded_at

    FROM {{ ref('raw_bookbuddy') }}
    WHERE TRIM(title) != ''
      AND TRIM(author) != ''
),

goodreads_normalized AS (
    SELECT
        -- Strip Goodreads ="..." ISBN wrapper, e.g. ="1234567890" -> "1234567890"
        NULLIF(REGEXP_REPLACE(TRIM(isbn),  '^="?|"?$', '', 'g'), '') AS isbn,
        NULLIF(REGEXP_REPLACE(TRIM(isbn13), '^="?|"?$', '', 'g'), '') AS isbn13,

        TRIM(title)                                        AS title,
        TRIM(author)                                       AS author,
        TRIM(publisher)                                    AS publisher,

        TRY_CAST(year_published AS INTEGER)                AS year,
        NULL                                               AS language,
        TRY_CAST(number_of_pages AS INTEGER)               AS pages,

        -- Domain detection signals (Goodreads uses bookshelves)
        ''                                                 AS category_lower,
        ''                                                 AS tags_lower,
        LOWER(TRIM(COALESCE(bookshelves, '')))             AS genre_lower,

        -- Rating normalization: integer string "0"-"5" -> NULL if 0
        CASE
            WHEN TRY_CAST(rating AS INTEGER) IS NULL THEN NULL
            WHEN TRY_CAST(rating AS INTEGER) = 0    THEN NULL
            ELSE TRY_CAST(rating AS INTEGER)
        END                                                AS rating,

        LOWER(TRIM(COALESCE(exclusive_shelf, '')))         AS status_raw,

        TRY_CAST(date_added AS DATE)                       AS date_added,
        TRY_CAST(date_read AS DATE)                        AS date_consumed,

        NULL                                               AS cover_url,
        NULLIF(TRIM(my_review), '')                        AS notes,
        NULL                                               AS series,
        NULL                                               AS volume,

        'goodreads'                                        AS source,
        _source,
        _loaded_at

    FROM {{ ref('raw_goodreads') }}
    WHERE TRIM(title) != ''
      AND TRIM(author) != ''
),

-- Combine both sources before deduplication
all_books AS (
    SELECT * FROM bookbuddy_normalized
    UNION ALL
    SELECT * FROM goodreads_normalized
),

-- Join publisher list for manga detection
manga_publishers AS (
    SELECT LOWER(TRIM(publisher)) AS publisher_lower
    FROM {{ ref('manga_publishers') }}
),

-- Join keyword mapping for manga detection
manga_keywords AS (
    SELECT LOWER(TRIM(source_value)) AS keyword
    FROM {{ ref('domain_mapping') }}
    WHERE domain = 'manga'
),

-- Detect domain per row using all available signals
domain_detected AS (
    SELECT
        b.*,

        CASE
            -- Signal 1: publisher is a known manga publisher
            WHEN EXISTS (
                SELECT 1 FROM manga_publishers mp
                WHERE LOWER(TRIM(b.publisher)) = mp.publisher_lower
            ) THEN 'manga'
            -- Signal 2: category or tags contain a manga keyword
            WHEN EXISTS (
                SELECT 1 FROM manga_keywords mk
                WHERE b.category_lower LIKE '%' || mk.keyword || '%'
                   OR b.tags_lower     LIKE '%' || mk.keyword || '%'
                   OR b.genre_lower    LIKE '%' || mk.keyword || '%'
            ) THEN 'manga'
            -- Default
            ELSE 'book'
        END                                                AS domain,

        -- Normalize status to unified vocabulary
        CASE
            WHEN status_raw IN ('read', 'finished', 'currently-reading') THEN 'read'
            WHEN status_raw IN ('to-read', 'unread', 'wishlist')         THEN 'unread'
            WHEN status_raw = 'previously_owned'                         THEN 'previously_owned'
            ELSE 'read'
        END                                                AS status

    FROM all_books b
),

-- Deduplication: one row per canonical item across both sources
-- Key: isbn13 -> isbn -> title + author
-- Priority: rating present > higher rating > oldest date_added
deduped AS (
    SELECT *
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY
                    COALESCE(
                        isbn13,
                        isbn,
                        LOWER(TRIM(author)) || '||' || LOWER(TRIM(title))
                    )
                ORDER BY
                    CASE WHEN rating IS NOT NULL THEN 0 ELSE 1 END ASC,
                    COALESCE(rating, 0) DESC,
                    date_added ASC
            ) AS rn
        FROM domain_detected
    )
    WHERE rn = 1
),

final AS (
    SELECT
        SHA256(
            domain || '|' || source || '|' ||
            COALESCE(
                isbn13,
                isbn,
                LOWER(author) || '||' || LOWER(title)
            )
        )                                   AS id,

        domain,
        source,
        COALESCE(isbn13, isbn, '')          AS source_id,

        title,
        author                              AS creator,
        year,
        language,
        pages,

        rating,
        status,
        date_added,
        date_consumed,
        cover_url,

        -- External IDs
        isbn,
        isbn13,

        series,
        volume,
        notes,
        _source,
        _loaded_at

    FROM deduped
)

SELECT * FROM final
