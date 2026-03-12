---
title: Series
---

# Series

```sql series_stats
select
    json_extract_string(details, '$.total_items')::integer as total_items,
    json_extract_string(details, '$.rated_items')::integer as rated_items
from tastebase.taste_profile
where stat_type = 'domain_stats' and dimension = 'series'
```

<BigValue data={series_stats} value=total_items title="Series" />
<BigValue data={series_stats} value=rated_items title="Rated" />

## Top rated series

```sql top_series
select
    rank_in_domain  as rank,
    title,
    creator,
    year,
    rating
from tastebase.top_rated
where domain = 'series'
order by rank_in_domain
limit 25
```

{#if top_series.length > 0}
<DataTable data={top_series}>
<Column id=rank title="#" />
<Column id=title title="Series" />
<Column id=creator title="Creator" />
<Column id=year title="Year" />
<Column id=rating title="★" />
</DataTable>
{:else}
<Note>No ratings yet for series. Rate series via the app to populate this section.</Note>
{/if}

## All series

```sql all_series
select
    title,
    creator,
    year,
    status,
    date_added::date as added_on
from tastebase.unified_tastes
where domain = 'series'
order by date_added desc
limit 100
```

<DataTable data={all_series}>
    <Column id=title title="Series" />
    <Column id=creator title="Creator" />
    <Column id=year title="Year" />
    <Column id=status title="Status" />
    <Column id=added_on title="Added" />
</DataTable>

## By decade

```sql series_decades
select
    dimension   as decade,
    value_int   as series_count
from tastebase.taste_profile
where stat_type = 'decade' and sub_dimension = 'series'
order by decade desc
```

{#if series_decades.length > 0}
<BarChart
    data={series_decades}
    x=decade
    y=series_count
    title="Series by decade"
/>
{:else}
<Note>No decade data available yet.</Note>
{/if}
