-- mart_top_rated.sql
-- Gold mart: top-rated items per domain, for dashboard widgets and agent queries.
-- Only rated items are included. Ties broken by date_added (oldest first).
-- The rank column allows consumers to filter to top-N per domain easily.

{{
    config(
        materialized='table',
        schema='gold'
    )
}}

WITH ranked AS (
    SELECT
        id,
        domain,
        source,
        title,
        creator,
        year,
        genres,
        rating,
        status,
        date_added,
        date_consumed,
        cover_url,
        external_ids,
        -- Rank within domain: 1 = highest rated (ties broken by earliest date_added)
        ROW_NUMBER() OVER (
            PARTITION BY domain
            ORDER BY rating DESC, date_added ASC
        ) AS rank_in_domain

    FROM {{ ref('mart_unified_tastes') }}

    WHERE rating IS NOT NULL
)

SELECT *
FROM ranked
-- Expose top 100 per domain (sufficient for all dashboard widgets)
WHERE rank_in_domain <= 100