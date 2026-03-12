---
title: Music
---

# Music

```sql music_stats
select
    json_extract_string(details, '$.total_items')::integer as total_items,
    json_extract_string(details, '$.rated_items')::integer as rated_items
from tastebase.taste_profile
where stat_type = 'domain_stats' and dimension = 'music'
```

<BigValue data={music_stats} value=total_items title="Albums" />
<BigValue data={music_stats} value=rated_items title="Rated" />

## Top rated albums

```sql top_music
select
    rank_in_domain  as rank,
    title,
    creator         as artist,
    year,
    rating
from tastebase.top_rated
where domain = 'music'
order by rank_in_domain
limit 25
```

{#if top_music.length > 0}
<DataTable data={top_music}>
<Column id=rank title="#" />
<Column id=title title="Album" />
<Column id=artist title="Artist" />
<Column id=year title="Year" />
<Column id=rating title="★" />
</DataTable>
{:else}
<Note>No ratings yet for music. Rate albums via the app to populate this section.</Note>
{/if}

## All albums

```sql all_music
select
    title,
    creator     as artist,
    year,
    status,
    date_added::date as added_on
from tastebase.unified_tastes
where domain = 'music'
order by date_added desc
limit 100
```

<DataTable data={all_music}>
    <Column id=title title="Album" />
    <Column id=artist title="Artist" />
    <Column id=year title="Year" />
    <Column id=status title="Status" />
    <Column id=added_on title="Added" />
</DataTable>

## Top artists

```sql top_music_creators
select
    dimension   as artist,
    value_int   as album_count
from tastebase.taste_profile
where stat_type = 'top_creator' and sub_dimension = 'music'
order by album_count desc
limit 20
```

{#if top_music_creators.length > 0}
<BarChart
    data={top_music_creators}
    x=artist
    y=album_count
    title="Most catalogued artists"
    swapXY=true
/>
{:else}
<Note>No creator data available yet.</Note>
{/if}
