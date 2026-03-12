-- raw_spotify.sql
-- Bronze layer — Spotify API raw data.
--
-- This model materializes the raw_spotify table written by SpotifyClient.
-- No transformation is applied here — data is stored exactly as received
-- from the Spotify Web API, with the JSON payload as a raw string.
--
-- Endpoints covered:
--   - saved_albums      : albums saved in the user's library
--   - recently_played   : last 50 played tracks
--   - top_artists       : top artists across short/medium/long term
--   - top_tracks        : top tracks across short/medium/long term
--
-- Audit columns injected by BaseLoader:
--   - _source     : always 'spotify'
--   - _loaded_at  : UTC timestamp of the ingestion run

{{ config(
    materialized='table',
    tags=['bronze', 'spotify']
) }}

SELECT
    -- Endpoint identifier: which Spotify API call produced this row
    endpoint,

    -- ISO 8601 UTC timestamp of when this batch was fetched
    fetched_at,

    -- Raw JSON payload from the Spotify API (stored as string)
    -- json_extract() in silver models will parse individual fields
    payload,

    -- Audit columns (injected by BaseLoader, never modified here)
    _source,
    _loaded_at

FROM raw_spotify