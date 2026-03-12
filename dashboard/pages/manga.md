---
title: Manga
---

# Manga

```sql manga_stats
select
    json_extract_string(details, '$.total_items')::integer as total_items,
    json_extract_string(details, '$.rated_items')::integer as rated_items,
    json_extract_string(details, '$.avg_rating')::float    as avg_rating,
    json_extract_string(details, '$.five_star')::integer   as five_star
from tastebase.taste_profile
where stat_type = 'domain_stats' and dimension = 'manga'
```

<BigValue data={manga_stats} value=total_items title="Manga" />
<BigValue data={manga_stats} value=rated_items title="Rated" />
<BigValue data={manga_stats} value=avg_rating title="Avg ★" fmt=num2 />
<BigValue data={manga_stats} value=five_star title="★★★★★" />

## Top rated manga

```sql top_manga
select
    rank_in_domain  as rank,
    title,
    creator         as author,
    year,
    rating
from tastebase.top_rated
where domain = 'manga'
order by rank_in_domain
limit 25
```

<DataTable data={top_manga}>
    <Column id=rank title="#" />
    <Column id=title title="Manga" />
    <Column id=author title="Author" />
    <Column id=year title="Year" />
    <Column id=rating title="★" />
</DataTable>

## Top authors

```sql top_manga_creators
select
    dimension   as author,
    value_int   as series_count,
    value_float as avg_rating
from tastebase.taste_profile
where stat_type = 'top_creator' and sub_dimension = 'manga'
order by series_count desc
limit 20
```

<BarChart
    data={top_manga_creators}
    x=author
    y=series_count
    title="Most read authors"
    swapXY=true
/>
