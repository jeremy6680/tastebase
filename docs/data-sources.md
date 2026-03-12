# Data Sources — Export & Rename Guide

> For each supported app, this page explains how to export your data
> and what filename to use so TasteBase can ingest it automatically.
>
> All CSV files must be placed in `data/raw/` with the exact filenames listed below.

---

## MusicBuddy (Kimico)

**App:** MusicBuddy  
**Target filename:** `data/raw/musicbuddy.csv`

### How to export

1. Open MusicBuddy on your device
2. Go to **Settings → Export**
3. Choose **CSV** format
4. Send the file to your computer (AirDrop, email, etc.)

### Rename

The exported file is named something like `MusicBuddy 2026-03-05 144228`.  
Rename it to exactly: `musicbuddy.csv`

---

## BookBuddy (Kimico)

**App:** BookBuddy  
**Target filename:** `data/raw/bookbuddy.csv`

### How to export

1. Open BookBuddy on your device
2. Go to **Settings → Export**
3. Choose **CSV** format

### Rename

The exported file is named something like `BookBuddy 2026-03-05 144228`.  
Rename it to exactly: `bookbuddy.csv`

---

## Goodreads

**App:** Goodreads (web)  
**Target filename:** `data/raw/goodreads.csv`

### How to export

1. Go to [goodreads.com/review/import](https://www.goodreads.com/review/import)
2. Click **Export Library**
3. Download the generated CSV file

### Rename

The exported file is named `goodreads-export.csv`.  
Rename it to exactly: `goodreads.csv`

---

## MovieBuddy (Kimico)

**App:** MovieBuddy  
**Target filename:** `data/raw/moviebuddy.csv`

### How to export

1. Open MovieBuddy on your device
2. Go to **Settings → Export**
3. Choose **CSV** format

### Rename

The exported file is named something like `MovieBuddy 2026-03-05 144228`.  
Rename it to exactly: `moviebuddy.csv`

---

## Letterboxd

**App:** Letterboxd (web)  
**Target filename:** `data/raw/letterboxd.csv`

### How to export

1. Go to [letterboxd.com/settings/data](https://letterboxd.com/settings/data)
2. Click **Export your data**
3. You will receive a `.zip` file by email
4. Unzip the archive — it contains several CSV files inside a folder
   named something like `letterboxd-username-2026-03-05-16-05-utc/`

### Which file to use

Inside the zip, use only the file named **`ratings.csv`**.  
Ignore the other files (`reviews.csv`, `watchlist.csv`, `diary.csv`, etc.).

### Rename

Rename `ratings.csv` to exactly: `letterboxd.csv`

---

## Spotify

Spotify data is fetched via API — no CSV export needed.  
See `.env.example` for the required credentials (`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`).

---

## Trakt.tv

Trakt.tv data is fetched via API — no CSV export needed.  
See `.env.example` for the required credentials (`TRAKT_CLIENT_ID`, `TRAKT_CLIENT_SECRET`).
