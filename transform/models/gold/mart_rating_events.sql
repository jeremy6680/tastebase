-- mart_rating_events.sql
-- Gold mart: append-only audit trail of rating changes.
-- Bootstrap: one INSERT event per imported rating (old_rating = NULL).
-- Subsequent user rating changes are inserted by the FastAPI backend
-- and are never modified or deleted (event sourcing pattern).
-- Running dbt run again is safe: the table is rebuilt from the bootstrap
-- snapshot; FastAPI-inserted events must be re-applied via the API.
-- Long-term: consider making this an incremental model in Phase 6.

{{
    config(
        materialized='table',
        schema='gold'
    )
}}

SELECT
    -- Stable event ID: hash of item + event type + rating value
    md5(id || '|bootstrap|' || COALESCE(rating::VARCHAR, 'null')) AS id,
    id              AS item_id,
    NULL::INTEGER   AS old_rating,      -- NULL = first-time import, no previous value
    rating          AS new_rating,
    'import'        AS changed_by,      -- 'import' | 'user'
    -- Approximate event time: when the bronze row was loaded
    _loaded_at      AS changed_at

FROM {{ ref('mart_unified_tastes') }}

-- Only create events for items that actually have a rating
WHERE rating IS NOT NULL