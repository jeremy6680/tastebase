-- Bronze model: raw_goodreads
--
-- Source: data/raw/goodreads.csv
-- Domain detection (book vs manga): deferred to silver (stg_books.sql)
-- Primary dedup key (silver): isbn13 → isbn → title + author
--
-- Note: Goodreads exports ISBN values wrapped in ="..." notation.
-- Stripping this wrapper is handled in the silver layer.

{{ config(materialized='table') }}

SELECT
    _source,
    _loaded_at,
    book_id,                -- Goodreads internal ID (not used for cross-source dedup)
    title,
    author,
    author_last_first,
    additional_authors,
    isbn,                   -- format: ="1234567890" — stripped in silver
    isbn13,                 -- primary dedup key; format: ="9781234567890"
    rating,                 -- integer string "0"–"5"; "0" = unrated
    average_rating,
    publisher,
    binding,
    number_of_pages,
    year_published,
    original_publication_year,
    date_read,
    date_added,
    bookshelves,            -- used for manga keyword detection in silver
    bookshelves_with_positions,
    exclusive_shelf,        -- read | currently-reading | to-read
    my_review,
    private_notes,
    read_count,
    owned_copies
FROM raw_goodreads