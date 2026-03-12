-- Bronze model: raw_bookbuddy
--
-- Source: data/raw/bookbuddy.csv
-- Domain detection (book vs manga): deferred to silver (stg_books.sql)
-- Primary dedup key (silver): isbn13 → isbn → title + author

{{ config(materialized='table') }}

SELECT
    _source,
    _loaded_at,
    title,
    original_title,
    series,
    volume,
    author,
    illustrator,
    translator,
    publisher,              -- used for manga publisher detection in silver
    year_published,
    original_year_published,
    edition,
    genre,
    format,
    language,
    original_language,
    isbn,                   -- fallback dedup key
    rating,                 -- float string "0.0"–"5.0"; "0" = unrated
    status,
    date_started,
    date_finished,
    date_added,
    tags,                   -- used for manga keyword detection in silver
    category,               -- used for manga detection in silver
    condition,
    quantity,
    wish_list,
    previously_owned,
    cover_url,
    google_volume_id,
    notes,
    recommended_by,
    number_of_pages,
    purchase_date,
    purchase_price,
    physical_location
FROM raw_bookbuddy