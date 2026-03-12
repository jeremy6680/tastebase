-- Bronze model: raw_musicbuddy
--
-- Materializes the raw_musicbuddy table created by MusicBuddyLoader
-- as a dbt-managed table. No transformation is applied here — this
-- model exists to register the bronze source in the dbt DAG and to
-- enable schema tests on raw data.
--
-- Source: data/raw/musicbuddy.csv (ingested by ingestion/csv/musicbuddy_loader.py)
-- Primary dedup key (used in silver): discogs_release_id
-- Fallback dedup key: upc_ean13

{{ config(materialized='table') }}

SELECT
    -- Audit columns (added by BaseLoader)
    _source,
    _loaded_at,

    -- Identity
    title,
    artist,
    content_type,       -- always "Album" for MusicBuddy exports

    -- Release info
    release_year,
    original_release_year,
    country,
    language,

    -- Classification
    genres,             -- raw string from Discogs, e.g. "Rock"
    styles,             -- raw string from Discogs, e.g. "Punk"
    media,              -- physical format: CD, Vinyl, Cassette, etc.
    format,
    category,

    -- Rating (normalized to 1–5 in silver, kept raw here)
    rating,             -- float string "0.000000" to "5.000000"; "0" = unrated

    -- Deduplication keys
    discogs_release_id, -- primary key for music dedup across sources
    upc_ean13,          -- fallback key

    -- Dates
    date_added,
    purchase_date,

    -- Enrichment
    cover_url,
    labels,
    catalog_number,
    tags,
    series,
    volume,
    length_seconds,
    tracks,             -- JSON string with track list and durations

    -- Ownership & condition
    condition,
    cover_condition,
    quantity,
    physical_location,
    wish_list,
    previously_owned,
    purchase_price,

    -- Free text
    notes

FROM raw_musicbuddy