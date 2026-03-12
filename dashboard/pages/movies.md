---
title: Movies
---

# Movies

```sql movies_stats
select
    json_extract_string(details, '$.total_items')::integer as total_items,
    json_extract_string(details, '$.rated_items')::integer as rated_items,
    json_extract_string(details, '$.avg_rating')::float    as avg_rating,
    json_extract_string(details, '$.five_star')::integer   as five_star
from tastebase.taste_profile
where stat_type = 'domain_stats' and dimension = 'movie'
```

<BigValue data={movies_stats} value=total_items title="Movies" />
<BigValue data={movies_stats} value=rated_items title="Rated" />
<BigValue data={movies_stats} value=avg_rating title="Avg ★" fmt=num2 />
<BigValue data={movies_stats} value=five_star title="★★★★★" />

## Top rated movies

```sql top_movies
select
    rank_in_domain  as rank,
    title,
    creator         as director,
    year,
    rating
from tastebase.top_rated
where domain = 'movie'
order by rank_in_domain
limit 25
```

<DataTable data={top_movies}>
    <Column id=rank title="#" />
    <Column id=title title="Movie" />
    <Column id=director title="Director" />
    <Column id=year title="Year" />
    <Column id=rating title="★" />
</DataTable>

## Top directors

```sql top_movie_creators
select
    dimension   as director,
    value_int   as movie_count,
    value_float as avg_rating
from tastebase.taste_profile
where stat_type = 'top_creator' and sub_dimension = 'movie'
order by movie_count desc
limit 20
```

<BarChart
    data={top_movie_creators}
    x=director
    y=movie_count
    title="Most watched directors"
    swapXY=true
/>

## By decade

```sql movie_decades
select
    dimension   as decade,
    value_int   as movie_count
from tastebase.taste_profile
where stat_type = 'decade' and sub_dimension = 'movie'
order by decade desc
```

<BarChart
    data={movie_decades}
    x=decade
    y=movie_count
    title="Movies by decade"
/>
