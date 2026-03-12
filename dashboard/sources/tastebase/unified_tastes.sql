-- Extract all unified taste items from the gold layer
SELECT
    id,
    domain,
    source,
    title,
    creator,
    year,
    status,
    date_added,
    date_consumed
FROM main_gold.mart_unified_tastes