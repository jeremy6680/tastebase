-- Extract current ratings for all items
SELECT
    item_id,
    rating,
    source,
    rated_at
FROM main_gold.mart_ratings