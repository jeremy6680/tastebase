-- mart_ratings.sql
-- Gold mart: current rating per item, with source tracking.
-- One row per item. Source = 'imported' for all ratings at this stage.
-- User ratings set via the FastAPI /ratings endpoint will be merged
-- in Phase 6 by updating this table directly (outside dbt).
-- Rebuilding with dbt run will restore imported ratings as the baseline.

{{
    config(
        materialized='table',
        schema='gold'
    )
}}

SELECT
    -- Stable rating ID: deterministic hash of item + source
    md5(id || '|imported') AS id,
    id                     AS item_id,
    rating,
    'imported'             AS source,   -- 'imported' | 'user' (user set via API)
    -- Use date_consumed as rated_at when available, else date_added, else today
    COALESCE(
        date_consumed,
        date_added,
        CURRENT_DATE
    )::TIMESTAMP           AS rated_at,
    NULL::VARCHAR          AS notes

FROM {{ ref('mart_unified_tastes') }}

-- Only expose items that have an actual rating
WHERE rating IS NOT NULL