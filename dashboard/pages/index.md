---
title: TasteBase — Overview
---

# TasteBase

My personal cultural taste warehouse — {total_items[0].total} items across {domain_count[0].count} domains.

```sql total_items
select sum(value_int) as total
from tastebase.taste_profile
where stat_type = 'domain_stats'
```

```sql domain_count
select count(distinct dimension) as count
from tastebase.taste_profile
where stat_type = 'domain_stats'
```

## Items per domain

```sql domain_stats
select
    dimension                           as domain,
    value_int                           as total_items,
    json_extract_string(details, '$.rated_items')::integer  as rated_items,
    json_extract_string(details, '$.avg_rating')::float     as avg_rating
from tastebase.taste_profile
where stat_type = 'domain_stats'
order by total_items desc
```

<DataTable data={domain_stats}>
    <Column id=domain title="Domain" />
    <Column id=total_items title="Total" />
    <Column id=rated_items title="Rated" />
    <Column id=avg_rating title="Avg ★" fmt=num2 />
</DataTable>

<BarChart
    data={domain_stats}
    x=domain
    y=total_items
    title="Items per domain"
    yAxisTitle="Items"
    swapXY=true
/>

## Top genres

```sql top_genres
select
    dimension as genre,
    value_int as item_count
from tastebase.taste_profile
where stat_type = 'top_genre'
order by item_count desc
limit 20
```

<BarChart
    data={top_genres}
    x=genre
    y=item_count
    title="Top 20 genres"
    swapXY=true
/>

## Top creators

```sql top_creators
select
    dimension   as creator,
    sub_dimension as domain,
    value_int   as item_count,
    value_float as avg_rating
from tastebase.taste_profile
where stat_type = 'top_creator'
order by item_count desc
limit 20
```

<DataTable data={top_creators}>
    <Column id=creator title="Creator" />
    <Column id=domain title="Domain" />
    <Column id=item_count title="Items" />
    <Column id=avg_rating title="Avg ★" fmt=num2 />
</DataTable>

## Decades

```sql decades
select
    dimension   as decade,
    sum(value_int) as item_count
from tastebase.taste_profile
where stat_type = 'decade'
group by decade
order by decade desc
```

<BarChart
    data={decades}
    x=decade
    y=item_count
    title="Items by decade"
    yAxisTitle="Items"
/>

## Recently added

```sql recently_added
select
    title,
    creator,
    domain,
    status,
    date_added::date as added_on
from tastebase.unified_tastes
where date_added is not null
order by date_added desc
limit 20
```

<DataTable data={recently_added}>
    <Column id=title title="Title" />
    <Column id=creator title="Creator" />
    <Column id=domain title="Domain" />
    <Column id=status title="Status" />
    <Column id=added_on title="Added" />
</DataTable>
