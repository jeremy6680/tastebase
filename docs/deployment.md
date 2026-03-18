# Deployment guide — TasteBase

> This guide covers self-hosted deployment on a Hetzner VPS managed via Coolify.
> All three services (API, agent, dashboard) run as Docker containers.

---

## Prerequisites

- A Hetzner VPS (CX21 or higher recommended — 2 vCPU, 4 GB RAM)
- Coolify installed on the VPS ([coolify.io/docs](https://coolify.io/docs))
- Docker and Docker Compose available on the server
- A domain name (optional but recommended for HTTPS)

---

## Architecture overview

```
Host VPS
├── api        (port 8000)  FastAPI — handles all DuckDB reads/writes
├── agent      (port 8080)  Chainlit + LangGraph conversational UI
└── dashboard  (port 3000)  Evidence.dev analytics dashboard

Volume: duckdb_data — persists warehouse.duckdb across restarts
```

All three services share a single Docker named volume (`duckdb_data`) that
contains `warehouse.duckdb`. The API is the only service that writes to it.

---

## 1. Prepare the VPS

```bash
# Connect to your VPS
ssh root@your-vps-ip

# Update system packages
apt-get update && apt-get upgrade -y

# Install Docker (if not already done by Coolify)
curl -fsSL https://get.docker.com | sh
```

---

## 2. Clone the repository

```bash
git clone https://github.com/jeremy6680/tastebase.git
cd tastebase
```

---

## 3. Configure environment variables

```bash
cp .env.example .env
nano .env
```

Fill in the required values:

```bash
# Required
DUCKDB_PATH=/app/data/warehouse.duckdb   # Must be this exact path in Docker
ANTHROPIC_API_KEY=your-anthropic-key
APP_SECRET_KEY=generate-a-strong-random-secret
APP_ENV=production

# Optional — Spotify enrichment (albums cover art, play counts)
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_ACCESS_TOKEN=
SPOTIFY_REFRESH_TOKEN=

# Optional — Trakt.tv watched history
TRAKT_CLIENT_ID=
TRAKT_CLIENT_SECRET=
TRAKT_ACCESS_TOKEN=
TRAKT_REFRESH_TOKEN=

# Agent
API_BASE_URL=http://api:8000   # Internal Docker network — do not change
AGENT_MODEL=claude-3-5-haiku-20241022
```

> ⚠️ `DUCKDB_PATH` must be `/app/data/warehouse.duckdb` in Docker.
> The relative path `data/warehouse.duckdb` only works for local development.

---

## 4. Build and start the stack

```bash
# Build all images and start the stack in detached mode
docker compose up --build -d

# Check that all three services are running
docker compose ps

# Follow logs for all services
docker compose logs -f

# Follow logs for a specific service
docker compose logs -f api
```

Expected output from `docker compose ps`:

```
NAME                  STATUS          PORTS
tastebase-api-1       Up (healthy)    0.0.0.0:8000->8000/tcp
tastebase-agent-1     Up              0.0.0.0:8080->8080/tcp
tastebase-dashboard-1 Up              0.0.0.0:3000->3000/tcp
```

---

## 5. Import your data

Once the stack is running, import your CSV exports via the API:

```bash
# Upload a CSV file and trigger the full pipeline
curl -X POST http://your-vps-ip:8000/ingest/upload \
  -F "source=musicbuddy" \
  -F "file=@/path/to/MusicBuddy-export.csv"

# Check ingestion status
curl http://your-vps-ip:8000/ingest/sources
```

Or use the Chainlit agent UI at `http://your-vps-ip:8080` to import and query data conversationally.

---

## 6. Set up Coolify (optional but recommended)

Coolify provides automatic HTTPS (via Let's Encrypt), rolling deployments, and a web UI for managing services.

### Add a new project in Coolify

1. Open the Coolify dashboard at `http://your-vps-ip:8000` (default Coolify port — check your install)
2. Click **New Project** → **Docker Compose**
3. Point to your repository or paste the `docker-compose.yml` content
4. Set environment variables in the Coolify UI (same values as your `.env`)
5. Add your domain and enable **HTTPS** (Coolify handles Let's Encrypt automatically)

### Recommended domain mapping

| Service   | Domain example                   |
| --------- | -------------------------------- |
| API       | `api.tastebase.yourdomain.com`   |
| Agent     | `agent.tastebase.yourdomain.com` |
| Dashboard | `dash.tastebase.yourdomain.com`  |

---

## 7. Backup and restore

The entire warehouse is a single file in the `duckdb_data` Docker volume.

```bash
# Backup — copy warehouse out of the volume to the host
docker run --rm \
  -v tastebase_duckdb_data:/data \
  -v $(pwd)/backups:/backup \
  alpine cp /data/warehouse.duckdb /backup/warehouse-$(date +%Y%m%d).duckdb

# Restore — copy a backup back into the volume
docker run --rm \
  -v tastebase_duckdb_data:/data \
  -v $(pwd)/backups:/backup \
  alpine cp /backup/warehouse-20260315.duckdb /data/warehouse.duckdb
```

> ⚠️ Stop the `api` service before restoring to avoid write conflicts:
> `docker compose stop api`

---

## 8. Updating TasteBase

```bash
# Pull the latest changes
git pull

# Rebuild images and restart services with zero downtime
docker compose up --build -d

# Run dbt migrations if the gold layer schema changed
docker compose exec api sh -c "cd /app/transform && dbt run"
```

---

## Troubleshooting

### API container exits immediately

Check the logs: `docker compose logs api`

Common causes:

- `DUCKDB_PATH` not set or not absolute → set it to `/app/data/warehouse.duckdb`
- `ANTHROPIC_API_KEY` missing → required for the agent, but the API itself starts without it

### Dashboard shows no data

The Evidence dashboard reads `warehouse.duckdb` from the `duckdb_data` volume.
If the volume is empty (first run), import data first via the API.

```bash
# Check if the warehouse file exists in the volume
docker run --rm -v tastebase_duckdb_data:/data alpine ls -lh /data/
```

### dbt run fails inside the container

```bash
# Run dbt manually inside the api container
docker compose exec api sh -c "cd /app/transform && dbt run"
```

Make sure `DUCKDB_PATH=/app/data/warehouse.duckdb` is set in `.env`.

### Agent cannot reach the API

The agent connects to `http://api:8000` via the internal Docker network.
If you changed `API_BASE_URL` to `localhost`, the agent cannot resolve the API container.
Reset it to `API_BASE_URL=http://api:8000`.
