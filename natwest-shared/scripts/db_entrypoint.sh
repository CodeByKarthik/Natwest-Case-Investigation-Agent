#!/usr/bin/env bash
set -e

echo "Waiting for PostgreSQL..."

until python - <<'PY'
import os
import psycopg

database_url = os.environ["DATABASE_URL"]
database_url = database_url.replace("postgresql+psycopg://", "postgresql://")

try:
    with psycopg.connect(database_url):
        pass
except Exception:
    raise SystemExit(1)
PY
do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is ready"

echo "Running Alembic schema migrations..."
alembic upgrade head

echo "Running database seed scripts..."
python -m natwest_shared.db.migrations.seed_users
python -m natwest_shared.db.migrations.seed_business_data

# ----- Add New Migrations Here -----

echo "Database initialization complete"