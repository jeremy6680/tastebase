-- raw_trakt.sql
-- Bronze layer — Trakt.tv API raw data.
--
-- This model materializes the raw_trakt table written by TraktClient.
-- No transformation is applied here — data is stored exactly as received
-- from the Trakt.tv API, with the JSON payload as a raw string.
--
-- Endpoints covered:
--   - watched_movies  : all movies marked as watched by the user
--   - watched_shows   : all shows marked as watched (series + anime)
--   - ratings_movies  : all movie ratings submitted by the user (scale 1–10)
--   - ratings_shows   : all show ratings submitted by the user (scale 1–10)
--
-- Note: Trakt ratings use a 1–10 integer scale.
-- Conversion to the unified 1–5 scale (CEIL(rating / 2.0)) happens
-- exclusively at the silver layer — never here.
--
-- Audit columns injected by BaseLoader:
--   - _source     : always 'trakt'
--   - _loaded_at  : UTC timestamp of the ingestion run

{{ config(
    materialized='table',
    tags=['bronze', 'trakt']
) }}

SELECT
    -- Endpoint identifier: which Trakt API call produced this row
    endpoint,

    -- ISO 8601 UTC timestamp of when this batch was fetched
    fetched_at,

    -- Raw JSON payload from the Trakt API (stored as string)
    -- json_extract() in silver models will parse individual fields
    payload,

    -- Audit columns (injected by BaseLoader, never modified here)
    _source,
    _loaded_at

FROM raw_trakt