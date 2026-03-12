---
title: Anime
---

# Anime

> ⚠️ Anime detection is a known gap (DEC-019). MovieBuddy exports genres via TMDB which uses
> "Animation" instead of "Anime", so detection returns 0 rows. This page will populate
> once the detection signal is improved (production country JP enrichment or anime seed).

```sql anime_items
select count(*) as total_items
from tastebase.unified_tastes
where domain = 'anime'
```

<BigValue data={anime_items} value=total_items title="Anime detected" />

## Top rated anime

```sql top_anime
select
    rank_in_domain  as rank,
    title,
    creator,
    year,
    rating
from tastebase.top_rated
where domain = 'anime'
order by rank_in_domain
limit 25
```

{#if top_anime.length > 0}
<DataTable data={top_anime}>
<Column id=rank title="#" />
<Column id=title title="Anime" />
<Column id=creator title="Studio / Creator" />
<Column id=year title="Year" />
<Column id=rating title="★" />
</DataTable>
{:else}
<Note>No anime detected yet. This will populate once the anime detection signal is improved.</Note>
{/if}

## All anime

```sql all_anime
select
    title,
    creator,
    year,
    status,
    date_added::date as added_on
from tastebase.unified_tastes
where domain = 'anime'
order by date_added desc
```

{#if all_anime.length > 0}
<DataTable data={all_anime}>
<Column id=title title="Anime" />
<Column id=creator title="Studio / Creator" />
<Column id=year title="Year" />
<Column id=status title="Status" />
<Column id=added_on title="Added" />
</DataTable>
{:else}
<Note>No anime items in the warehouse yet.</Note>
{/if}
