-- raw_spotify.sql
-- Bronze layer — Spotify API raw data.
--
-- This model materializes the raw_spotify table written by SpotifyClient.
-- No transformation is applied — data is stored exactly as received from
-- the Spotify Web API.
--
-- The pre-hook ensures the source table (main.raw_spotify) always exists,
-- even when Spotify ingestion hasn't run yet (e.g. rate-limited).
-- When Spotify is ingested, make ingest populates main.raw_spotify,
-- and the next dbt run picks up the real data automatically.
--
-- Endpoints covered:
--   - saved_albums, recently_played, top_artists, top_tracks
--
-- Audit columns: _source = 'spotify', _loaded_at = UTC timestamp

{{ config(
    materialized='table',
    tags=['bronze', 'spotify'],
    pre_hook="
        CREATE TABLE IF NOT EXISTS main.raw_spotify (
            endpoint    VARCHAR,
            fetched_at  VARCHAR,
            payload     VARCHAR,
            _source     VARCHAR,
            _loaded_at  TIMESTAMPTZ
        )
    "
) }}

SELECT
    endpoint,
    fetched_at,
    payload,
    _source,
    _loaded_at
FROM main.raw_spotify