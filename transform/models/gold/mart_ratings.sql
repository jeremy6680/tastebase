-- mart_ratings.sql
-- Gold mart: current rating per item, with source tracking.
-- One row per item.
--
-- Materialization: incremental (DEC-030)
--   - On first run: inserts all rated items from mart_unified_tastes.
--   - On subsequent runs: only inserts items whose item_id does NOT already
--     exist in mart_ratings. This preserves user ratings (source='user')
--     set via the FastAPI /ratings endpoint across pipeline rebuilds.
--   - User ratings are NEVER overwritten by dbt.
--   - unique_key = 'item_id': if the same item_id arrives again from the
--     pipeline, it is skipped (do_nothing strategy).
--
-- See DECISIONS.md DEC-030.

{{
    config(
        materialized='incremental',
        schema='gold',
        unique_key='item_id',
        incremental_strategy='append',
        on_schema_change='ignore'
    )
}}

SELECT
    md5(id || '|imported') AS id,
    id                     AS item_id,
    rating,
    'imported'             AS source,
    COALESCE(
        date_consumed,
        date_added,
        CURRENT_DATE
    )::TIMESTAMP           AS rated_at,
    NULL::VARCHAR          AS notes

FROM {{ ref('mart_unified_tastes') }}

WHERE rating IS NOT NULL

{% if is_incremental() %}
  -- On incremental runs: only insert items not already in mart_ratings.
  -- This is what protects user ratings from being overwritten.
  AND id NOT IN (SELECT item_id FROM {{ this }})
{% endif %}
