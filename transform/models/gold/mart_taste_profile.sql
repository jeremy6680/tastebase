-- mart_taste_profile.sql
-- Gold mart: aggregate taste statistics for the agent and dashboard.
-- Covers: item counts per domain, rating distributions, top genres,
-- top creators, and decade breakdown — all computed from mart_unified_tastes.

{{
    config(
        materialized='table',
        schema='gold'
    )
}}

-- 1. Item counts and rating stats per domain
WITH domain_stats AS (
    SELECT
        domain,
        COUNT(*)                        AS total_items,
        COUNT(rating)                   AS rated_items,
        ROUND(AVG(rating), 2)           AS avg_rating,
        COUNT(*) FILTER (WHERE rating = 5) AS five_star_count,
        COUNT(*) FILTER (WHERE rating = 4) AS four_star_count,
        COUNT(*) FILTER (WHERE rating = 3) AS three_star_count,
        COUNT(*) FILTER (WHERE rating = 2) AS two_star_count,
        COUNT(*) FILTER (WHERE rating = 1) AS one_star_count
    FROM {{ ref('mart_unified_tastes') }}
    GROUP BY domain
),

-- 2. Top genres overall (genres is a plain VARCHAR — split on comma)
-- stg_books has no genres column (NULL), so those rows are excluded naturally
genre_counts AS (
    SELECT
        TRIM(genre_value)   AS genre,
        COUNT(*)            AS item_count
    FROM {{ ref('mart_unified_tastes') }},
        -- Unnest comma-separated genres string into individual rows
        UNNEST(
            string_split(COALESCE(genres, ''), ',')
        ) AS t(genre_value)
    WHERE genres IS NOT NULL
      AND TRIM(genre_value) != ''
    GROUP BY TRIM(genre_value)
    ORDER BY item_count DESC
    LIMIT 30
),

-- 3. Top creators overall (min 2 items to filter noise)
top_creators AS (
    SELECT
        creator,
        domain,
        COUNT(*)            AS item_count,
        ROUND(AVG(rating), 2) AS avg_rating
    FROM {{ ref('mart_unified_tastes') }}
    WHERE creator IS NOT NULL
    GROUP BY creator, domain
    HAVING COUNT(*) >= 2
    ORDER BY item_count DESC, avg_rating DESC
    LIMIT 50
),

-- 4. Decade breakdown (items with a known year)
decade_breakdown AS (
    SELECT
        (year // 10 * 10)::VARCHAR || 's'  AS decade,
        domain,
        COUNT(*)                            AS item_count,
        ROUND(AVG(rating), 2)               AS avg_rating
    FROM {{ ref('mart_unified_tastes') }}
    WHERE year IS NOT NULL
      AND year BETWEEN 1900 AND 2100         -- guard against garbage years
    GROUP BY (year // 10 * 10), domain
    ORDER BY decade DESC
)

-- Final output: one row per stat_type + dimension value
-- Structured for easy agent queries: SELECT * FROM mart_taste_profile WHERE stat_type = 'domain_stats'

SELECT
    'domain_stats'  AS stat_type,
    domain          AS dimension,
    NULL            AS sub_dimension,
    total_items::VARCHAR    AS value_text,
    total_items             AS value_int,
    avg_rating              AS value_float,
    json_object(
        'total_items',    total_items,
        'rated_items',    rated_items,
        'avg_rating',     avg_rating,
        'five_star',      five_star_count,
        'four_star',      four_star_count,
        'three_star',     three_star_count,
        'two_star',       two_star_count,
        'one_star',       one_star_count
    ) AS details

FROM domain_stats

UNION ALL

SELECT
    'top_genre'     AS stat_type,
    genre           AS dimension,
    NULL            AS sub_dimension,
    item_count::VARCHAR AS value_text,
    item_count          AS value_int,
    NULL                AS value_float,
    json_object('item_count', item_count) AS details

FROM genre_counts

UNION ALL

SELECT
    'top_creator'   AS stat_type,
    creator         AS dimension,
    domain          AS sub_dimension,
    item_count::VARCHAR AS value_text,
    item_count          AS value_int,
    avg_rating          AS value_float,
    json_object(
        'item_count', item_count,
        'avg_rating', avg_rating,
        'domain',     domain
    ) AS details

FROM top_creators

UNION ALL

SELECT
    'decade'        AS stat_type,
    decade          AS dimension,
    domain          AS sub_dimension,
    item_count::VARCHAR AS value_text,
    item_count          AS value_int,
    avg_rating          AS value_float,
    json_object(
        'item_count', item_count,
        'avg_rating', avg_rating,
        'domain',     domain
    ) AS details

FROM decade_breakdown