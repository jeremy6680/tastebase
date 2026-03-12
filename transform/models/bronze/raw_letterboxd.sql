-- Bronze model: raw_letterboxd
--
-- Source: data/raw/letterboxd.csv (renamed from ratings.csv in export zip)
-- Domain: always "movie" — Letterboxd is a movies-only source
-- Primary dedup key (silver): imdb_id (enriched later) → title + release_year
--
-- Note: Letterboxd CSV has only 5 columns. No IMDB ID is present in the
-- export — cross-source dedup with MovieBuddy relies on title + release_year
-- until TMDB enrichment is added in a future phase.

{{ config(materialized='table') }}

SELECT
    _source,
    _loaded_at,
    title,
    release_year,
    rating,                 -- float string "0.5"–"5.0" in 0.5 increments
    letterboxd_uri,         -- unique identifier for this entry in Letterboxd
    date_added              -- date the rating was logged on Letterboxd
FROM raw_letterboxd