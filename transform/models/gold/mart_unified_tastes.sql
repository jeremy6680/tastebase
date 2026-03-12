-- mart_unified_tastes.sql
-- Gold mart: unified view of all taste domains.
-- One row per deduplicated item. Consumes all silver stg_ views.
-- The item ID is inherited from the silver layer (already MD5-hashed).
-- external_ids is a JSON object capturing all domain-specific identifiers.

{{
    config(
        materialized='table',
        schema='gold'
    )
}}

-- Music items (MusicBuddy primary + Spotify enrichment)
SELECT
    id,
    domain,
    source,
    source_id,
    title,
    creator,
    year,
    genres,
    rating,
    status,
    date_added,
    date_consumed,
    cover_url,
    -- Music-specific external identifiers
    json_object(
        'discogs_release_id', discogs_release_id,
        'upc_ean13',          upc_ean13,
        'spotify_id',         spotify_id
    ) AS external_ids,
    -- Music-specific metadata (stored in notes for cross-domain uniformity)
    notes,
    _source,
    _loaded_at

FROM {{ ref('stg_music') }}

UNION ALL

-- Book and manga items (BookBuddy + Goodreads, manga detection applied)
SELECT
    id,
    domain,
    source,
    source_id,
    title,
    creator,
    year,
    NULL AS genres,         -- stg_books has no genres column
    rating,
    status,
    date_added,
    date_consumed,
    cover_url,
    json_object(
        'isbn',   isbn,
        'isbn13', isbn13
    ) AS external_ids,
    notes,
    _source,
    _loaded_at

FROM {{ ref('stg_books') }}

UNION ALL

-- Movie items (MovieBuddy + Letterboxd + Trakt)
SELECT
    id,
    domain,
    source,
    source_id,
    title,
    creator,
    year,
    genres,
    rating,
    status,
    date_added,
    date_consumed,
    cover_url,
    json_object(
        'imdb_id', imdb_id,
        'tmdb_id', tmdb_id
    ) AS external_ids,
    notes,
    _source,
    _loaded_at

FROM {{ ref('stg_movies') }}

UNION ALL

-- Series items (Trakt shows, anime excluded)
SELECT
    id,
    domain,
    source,
    source_id,
    title,
    creator,
    year,
    genres,
    rating,
    status,
    date_added,
    date_consumed,
    cover_url,
    json_object(
        'imdb_id', imdb_id,
        'tmdb_id', tmdb_id
    ) AS external_ids,
    notes,
    _source,
    _loaded_at

FROM {{ ref('stg_series') }}

UNION ALL

-- Anime items (MovieBuddy TV Show + Trakt anime genre)
-- Currently 0 rows due to TMDB genre signal gap (see DECISIONS.md DEC-019)
SELECT
    id,
    domain,
    source,
    source_id,
    title,
    creator,
    year,
    genres,
    rating,
    status,
    date_added,
    date_consumed,
    cover_url,
    json_object(
        'imdb_id', imdb_id,
        'tmdb_id', tmdb_id
    ) AS external_ids,
    notes,
    _source,
    _loaded_at

FROM {{ ref('stg_anime') }}