# SalesLens Backend Scripts

Utility scripts for database initialization, maintenance, and administration.

## Available Scripts

### `init_defaults.py`

Initialize default data for tenants (prompt templates, etc.).

**When to run:**
- After creating a new tenant
- During initial deployment
- After updating default prompt templates

**Usage:**
```bash
# Inside backend container
docker compose exec app python scripts/init_defaults.py

# Or directly with Python (if DB is accessible)
cd backend
python scripts/init_defaults.py
```

**What it does:**
- Creates default "Call Analysis" prompt template for each tenant
- Skips tenants that already have active templates
- Idempotent - safe to run multiple times

## Creating New Scripts

When adding new initialization scripts:

1. Make them idempotent (safe to run multiple times)
2. Add proper error handling and rollback
3. Print clear progress messages
4. Update this README
5. Consider adding to deployment automation
