-- Bronze model: raw_moviebuddy
--
-- Source: data/raw/moviebuddy.csv
-- Domain detection: deferred to silver
--   content_type = "Movie"                          → movie
--   content_type = "TV Show" + genres like "Anime"  → anime
--   content_type = "TV Show" + no anime genre        → series
-- Primary dedup key (silver): imdb_id → tmdb_id → title + release_year
--
-- Note: "cast" is a reserved word in DuckDB and must be quoted.

{{ config(materialized='table') }}

SELECT
    _source,
    _loaded_at,
    title,
    original_title,
    content_type,           -- "Movie" or "TV Show" — primary domain signal
    series,
    volume,
    runtime,
    release_year,
    original_release_year,
    first_air_year,
    last_air_year,
    number_of_seasons,
    genres,                 -- used for anime detection: contains "Anime"
    directors,
    tv_creators,
    tv_networks,
    "cast",                 -- quoted: reserved word in DuckDB
    languages,
    summary,
    film_rating,
    imdb_id,                -- primary dedup key
    tmdb_id,                -- fallback dedup key
    rating,                 -- float string "0.0"–"5.0"; "0" = unrated
    status,
    date_finished,
    date_added,
    tags,
    category,
    condition,
    quantity,
    wish_list,
    previously_owned,
    cover_url,
    notes,
    recommended_by,
    tv_season,
    number_of_discs,
    production_countries,
    purchase_date,
    purchase_price,
    physical_location
FROM raw_moviebuddy