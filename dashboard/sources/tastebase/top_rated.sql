-- Extract top-rated items per domain, including rank for ordering
SELECT
    id,
    domain,
    title,
    creator,
    year,
    genres,
    rating,
    status,
    rank_in_domain
FROM main_gold.mart_top_rated