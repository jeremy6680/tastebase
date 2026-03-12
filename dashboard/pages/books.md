---
title: Books
---

# Books

```sql books_stats
select
    json_extract_string(details, '$.total_items')::integer as total_items,
    json_extract_string(details, '$.rated_items')::integer as rated_items,
    json_extract_string(details, '$.avg_rating')::float    as avg_rating,
    json_extract_string(details, '$.five_star')::integer   as five_star
from tastebase.taste_profile
where stat_type = 'domain_stats' and dimension = 'book'
```

<BigValue data={books_stats} value=total_items title="Books" />
<BigValue data={books_stats} value=rated_items title="Rated" />
<BigValue data={books_stats} value=avg_rating title="Avg ★" fmt=num2 />
<BigValue data={books_stats} value=five_star title="★★★★★" />

## Top rated books

```sql top_books
select
    rank_in_domain  as rank,
    title,
    creator         as author,
    year,
    rating
from tastebase.top_rated
where domain = 'book'
order by rank_in_domain
limit 25
```

<DataTable data={top_books}>
    <Column id=rank title="#" />
    <Column id=title title="Book" />
    <Column id=author title="Author" />
    <Column id=year title="Year" />
    <Column id=rating title="★" />
</DataTable>

## Top authors

```sql top_book_creators
select
    dimension   as author,
    value_int   as book_count,
    value_float as avg_rating
from tastebase.taste_profile
where stat_type = 'top_creator' and sub_dimension = 'book'
order by book_count desc
limit 20
```

<BarChart
    data={top_book_creators}
    x=author
    y=book_count
    title="Most read authors"
    swapXY=true
/>
