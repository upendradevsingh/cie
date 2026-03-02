# SalesLens Deployment Guide

This document covers deploying SalesLens from development through production, including Docker setup, environment configuration, database migrations, security hardening, and scaling strategies.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Docker Deployment](#docker-deployment)
- [Environment Variables Reference](#environment-variables-reference)
- [Database Migrations](#database-migrations)
- [Production Considerations](#production-considerations)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Security Hardening](#security-hardening)
- [Backup Strategy](#backup-strategy)
- [Scaling](#scaling)
- [Monitoring and Health Checks](#monitoring-and-health-checks)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Minimum Version | Purpose |
|---|---|---|
| Docker | 20.10+ | Container runtime |
| Docker Compose | 2.0+ | Multi-container orchestration |
| Git | 2.30+ | Source code management |

### Required API Keys

| Service | Purpose | Where to Get |
|---|---|---|
| Deepgram | Speech-to-text transcription | [console.deepgram.com](https://console.deepgram.com) |
| OpenAI | LLM analysis + Whisper fallback | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |

### System Requirements

| Tier | CPU | RAM | Storage | Suitable For |
|---|---|---|---|---|
| Minimum | 2 cores | 4 GB | 20 GB | Evaluation, small team (<5 agents) |
| Recommended | 4 cores | 8 GB | 100 GB | Production, medium team (5-25 agents) |
| Large | 8+ cores | 16+ GB | 500 GB+ | High volume (25+ agents, 100+ calls/day) |

Storage needs grow with call volume. Budget approximately 10 MB per minute of audio for recordings stored locally.

---

## Docker Deployment

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/saleslens.git
cd saleslens
```

### Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum these three values:

```bash
# Generate a secure secret key
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# Set these in .env:
SECRET_KEY=<output-from-above>
DEEPGRAM_API_KEY=<your-deepgram-key>
OPENAI_API_KEY=<your-openai-key>
```

For production, also update:

```bash
# Use a strong database password
DATABASE_URL=postgresql://saleslens:<strong-password>@postgres:5432/saleslens

# Restrict CORS to your actual domain
CORS_ORIGINS=https://app.yourdomain.com
```

### Step 3: Build and Start Services

```bash
# Build all images
docker-compose build

# Start in detached mode
docker-compose up -d
```

### Step 4: Verify Deployment

```bash
# Check all services are running
docker-compose ps

# Expected output:
# NAME                STATUS              PORTS
# saleslens-app       Up (healthy)        0.0.0.0:8000->8000/tcp
# saleslens-worker    Up (healthy)
# saleslens-postgres  Up (healthy)        0.0.0.0:5432->5432/tcp
# saleslens-redis     Up (healthy)        0.0.0.0:6379->6379/tcp
# saleslens-frontend  Up                  0.0.0.0:3000->80/tcp

# Test API health
curl http://localhost:8000/health
# {"status":"healthy","service":"SalesLens","version":"0.1.0"}
```

### Step 5: Create Initial Tenant

```bash
curl -X POST http://localhost:8000/api/v1/auth/tenant \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Your Company",
    "tenant_slug": "your-company",
    "admin_email": "admin@yourcompany.com",
    "admin_password": "a-secure-password-here",
    "admin_name": "Admin User"
  }'
```

Save the `access_token` from the response.

### Step 6: Access the Application

| Service | URL |
|---|---|
| Frontend Dashboard | http://localhost:3000 |
| API (Swagger) | http://localhost:8000/docs |

---

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | JWT signing key (32+ random chars) | `dKj8x2m...` |
| `DEEPGRAM_API_KEY` | Deepgram API key | `dg-...` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |

### Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://saleslens:saleslens_password@postgres:5432/saleslens` | PostgreSQL connection string |

### Redis

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |

### Security

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me-...` | JWT signing secret |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Token lifetime (24 hours) |

### Transcription

| Variable | Default | Description |
|---|---|---|
| `TRANSCRIPTION_PROVIDER` | `deepgram` | Provider: `deepgram` or `whisper` |
| `DEEPGRAM_API_KEY` | -- | Deepgram API key |

### LLM

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | LLM provider |
| `LLM_MODEL` | `gpt-4o-mini` | Model for analysis |
| `LLM_QA_MODEL` | `gpt-4o` | Model for QA sampling |

### Storage

| Variable | Default | Description |
|---|---|---|
| `UPLOAD_DIR` | `/app/uploads` | Local upload directory |
| `MAX_FILE_SIZE_MB` | `100` | Max upload size |
| `S3_BUCKET` | -- | S3 bucket (optional) |
| `S3_REGION` | -- | S3 region (optional) |
| `AWS_ACCESS_KEY_ID` | -- | AWS key (optional) |
| `AWS_SECRET_ACCESS_KEY` | -- | AWS secret (optional) |
| `S3_ENDPOINT_URL` | -- | Custom S3 endpoint (optional) |

### CORS

| Variable | Default | Description |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Allowed origins (comma-separated) |

### Email

| Variable | Default | Description |
|---|---|---|
| `SMTP_HOST` | -- | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | -- | SMTP username |
| `SMTP_PASSWORD` | -- | SMTP password |
| `SMTP_USE_TLS` | `true` | Use TLS for SMTP |
| `REPORT_FROM_EMAIL` | `reports@saleslens.ai` | Sender email for reports |

### Celery

| Variable | Default | Description |
|---|---|---|
| `CELERY_WORKER_CONCURRENCY` | `4` | Number of concurrent worker processes |
| `CELERY_TASK_SOFT_TIME_LIMIT` | `600` | Soft time limit per task (seconds) |
| `CELERY_TASK_TIME_LIMIT` | `900` | Hard time limit per task (seconds) |

### Logging

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `LOG_FORMAT` | `json` | Log format: `json` or `text` |

---

## Database Migrations

SalesLens uses Alembic for database schema migrations.

### On First Run

The application automatically creates all tables on startup via `Base.metadata.create_all()`. For production, use Alembic migrations instead.

### Running Migrations Manually

```bash
# Enter the backend container
docker-compose exec app bash

# Check current migration state
alembic current

# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Rollback one migration
alembic downgrade -1

# Rollback to a specific revision
alembic downgrade <revision_id>
```

### Migration Best Practices

1. Always review auto-generated migrations before applying. Check for unintended changes.
2. Test migrations on a staging database before applying to production.
3. Back up the database before running migrations in production.
4. Never delete migration files that have been applied to production.

---

## Production Considerations

### SSL/TLS Configuration

For production, place a reverse proxy (nginx, Caddy, or Traefik) in front of the application to handle TLS termination.

#### Using nginx

Add an nginx service to your `docker-compose.override.yml`:

```yaml
services:
  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - app
      - frontend
```

Example `nginx.conf`:

```nginx
server {
    listen 80;
    server_name app.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name app.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/app.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.yourdomain.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API
    location /api/ {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 100m;
    }

    # Health check
    location /health {
        proxy_pass http://app:8000;
    }

    # API docs
    location /docs {
        proxy_pass http://app:8000;
    }
    location /redoc {
        proxy_pass http://app:8000;
    }
    location /openapi.json {
        proxy_pass http://app:8000;
    }
}
```

#### Using Caddy (simpler, auto-HTTPS)

```
app.yourdomain.com {
    handle /api/* {
        reverse_proxy app:8000
    }
    handle /health {
        reverse_proxy app:8000
    }
    handle /docs {
        reverse_proxy app:8000
    }
    handle {
        reverse_proxy frontend:80
    }
}
```

---

## Security Hardening

### Secret Key

Generate a cryptographically secure secret key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Never use the default value in production. Rotate the key periodically (requires all existing tokens to be re-issued).

### Database Security

1. **Change the default password**: Update the PostgreSQL password in both `docker-compose.yml` and `.env`.
2. **Restrict network access**: In production, remove the `ports:` mapping for PostgreSQL and Redis. The application containers connect via the Docker network; they do not need exposed ports.

```yaml
# docker-compose.override.yml (production)
services:
  postgres:
    ports: []  # Remove external port
  redis:
    ports: []  # Remove external port
```

3. **Enable SSL for PostgreSQL connections** if the database is on a separate host:
   ```
   DATABASE_URL=postgresql://saleslens:password@db-host:5432/saleslens?sslmode=require
   ```

### CORS

Restrict to your actual frontend domain:

```
CORS_ORIGINS=https://app.yourdomain.com
```

### Token Expiration

For higher security environments, reduce token lifetime:

```
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### File Upload Security

- The API validates file extensions (only mp3, wav, m4a, webm).
- Maximum file size is enforced (default 100 MB).
- Uploaded files are stored in a volume, not served directly.

---

## Backup Strategy

### Database Backups

#### Automated Daily Backups

Create a backup script:

```bash
#!/bin/bash
# backup-db.sh
BACKUP_DIR=/backups/saleslens
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/saleslens_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

docker-compose exec -T postgres pg_dump \
  -U saleslens \
  -d saleslens \
  --no-owner \
  --no-acl \
  | gzip > "$BACKUP_FILE"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "Backup saved to: $BACKUP_FILE"
```

Schedule with cron:

```cron
0 2 * * * /opt/saleslens/backup-db.sh >> /var/log/saleslens-backup.log 2>&1
```

#### Restoring from Backup

```bash
# Stop the application (keep postgres running)
docker-compose stop app worker frontend

# Restore
gunzip < /backups/saleslens/saleslens_20260301_020000.sql.gz \
  | docker-compose exec -T postgres psql -U saleslens -d saleslens

# Restart services
docker-compose start app worker frontend
```

### Upload Storage Backups

If using local storage, back up the Docker volume:

```bash
# Export volume to tar
docker run --rm \
  -v saleslens_upload_data:/data \
  -v /backups:/backups \
  alpine tar czf /backups/uploads_$(date +%Y%m%d).tar.gz -C /data .
```

If using S3, enable bucket versioning for built-in backup protection.

---

## Scaling

### Horizontal Worker Scaling

Add more Celery workers to process calls faster:

```bash
# Scale workers to 3 instances
docker-compose up -d --scale worker=3
```

Each worker runs with the configured concurrency (default: 4 processes), so 3 workers handle 12 calls concurrently.

### Dedicated Task Queues

For high-volume deployments, run separate workers for different task types:

```yaml
# docker-compose.override.yml
services:
  worker-transcription:
    extends:
      service: worker
    command: >
      celery -A app.tasks worker
      --loglevel=info
      --concurrency=4
      -Q transcription

  worker-analysis:
    extends:
      service: worker
    command: >
      celery -A app.tasks worker
      --loglevel=info
      --concurrency=4
      -Q analysis

  worker-reports:
    extends:
      service: worker
    command: >
      celery -A app.tasks worker
      --loglevel=info
      --concurrency=2
      -Q reports
```

### Backend Scaling

The FastAPI backend runs with 4 uvicorn workers by default. To handle more concurrent API requests:

```yaml
# docker-compose.override.yml
services:
  app:
    command: >
      uvicorn app.main:app
      --host 0.0.0.0
      --port 8000
      --workers 8
      --log-level info
```

For even higher throughput, run multiple app containers behind a load balancer:

```bash
docker-compose up -d --scale app=3
```

Add nginx or a load balancer in front to distribute requests across instances.

### Database Scaling

#### Connection Pooling

For high connection counts, add PgBouncer:

```yaml
# docker-compose.override.yml
services:
  pgbouncer:
    image: edoburu/pgbouncer
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://saleslens:password@postgres:5432/saleslens
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 200
      DEFAULT_POOL_SIZE: 25
    depends_on:
      - postgres
```

Update `DATABASE_URL` to point to PgBouncer instead of PostgreSQL directly.

#### Read Replicas

For read-heavy workloads (analytics, reports), configure PostgreSQL streaming replication and point analytics queries to the replica:

```
DATABASE_URL=postgresql://saleslens:password@primary:5432/saleslens
DATABASE_READ_URL=postgresql://saleslens:password@replica:5432/saleslens
```

---

## Monitoring and Health Checks

### Built-in Health Checks

SalesLens provides health check endpoints used by Docker and external monitoring:

| Endpoint | Service | Description |
|---|---|---|
| `GET /health` | Backend API | Returns `{"status": "healthy"}` |
| Docker HEALTHCHECK | PostgreSQL | `pg_isready` |
| Docker HEALTHCHECK | Redis | `redis-cli ping` |
| Docker HEALTHCHECK | Celery Worker | `celery inspect ping` |

### Monitoring Checklist

Monitor these metrics in production:

**Application**:
- API response times (P50, P95, P99)
- Error rate (5xx responses)
- Active connections

**Celery Workers**:
- Queue depth (number of pending tasks)
- Task completion rate
- Task failure rate
- Average processing time per call

**Database**:
- Active connections
- Query latency
- Disk usage
- Replication lag (if using replicas)

**Redis**:
- Memory usage
- Connected clients
- Key eviction rate

**System**:
- CPU usage
- Memory usage
- Disk I/O
- Network throughput

### Log Aggregation

SalesLens outputs structured JSON logs by default. Aggregate logs using your preferred stack:

```bash
# View real-time logs
docker-compose logs -f app worker

# Export to file
docker-compose logs --no-color > saleslens-logs.txt
```

For production, configure log forwarding to a centralized system (ELK, Datadog, CloudWatch, etc.) by mounting a log driver:

```yaml
# docker-compose.override.yml
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"
```

---

## Troubleshooting

### Services Not Starting

```bash
# Check service logs
docker-compose logs postgres
docker-compose logs redis
docker-compose logs app
docker-compose logs worker

# Common issues:
# - PostgreSQL: Permission errors on data volume
# - App: Missing environment variables or bad database URL
# - Worker: Cannot connect to Redis or PostgreSQL
```

### Database Connection Refused

```bash
# Verify PostgreSQL is healthy
docker-compose exec postgres pg_isready -U saleslens

# Check if the database exists
docker-compose exec postgres psql -U saleslens -c "\\l"

# Test connection from the app container
docker-compose exec app python -c "
from app.db.session import engine
with engine.connect() as conn:
    print('Connection successful')
"
```

### Celery Worker Not Processing Tasks

```bash
# Check worker status
docker-compose exec worker celery -A app.tasks inspect active

# Check queue depth
docker-compose exec worker celery -A app.tasks inspect reserved

# Check for errors
docker-compose logs worker --tail=50
```

### Call Stuck in "uploaded" or "transcribing" Status

```bash
# Check if the worker picked up the task
docker-compose logs worker | grep <call-id>

# Check Redis for queued tasks
docker-compose exec redis redis-cli LLEN celery

# Retry processing manually
docker-compose exec app python -c "
from app.tasks.process_call import process_call
process_call.delay('<call-id>')
print('Task re-queued')
"
```

### High Memory Usage

```bash
# Check container resource usage
docker stats

# Common causes:
# - Large audio files being held in memory during transcription
# - PostgreSQL not tuned for available memory
# - Redis maxmemory not configured (set in docker-compose.yml)
```

### Resetting Everything

If you need to start completely fresh:

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Rebuild and restart
docker-compose up -d --build
```
