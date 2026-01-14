#!/bin/bash
set -e

echo "==> Starting Reddit Scout deployment..."

# Parse database URL to extract components
# Expected format: postgresql+asyncpg://user:pass@host:port/dbname
if [[ -n "$DATABASE_URL" ]]; then
    # Convert asyncpg URL to psql-compatible format for database creation
    PSQL_URL=$(echo "$DATABASE_URL" | sed 's/postgresql+asyncpg/postgresql/')

    # Extract database name from URL
    DB_NAME=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')

    # Extract connection string without database name (for creating db)
    BASE_URL=$(echo "$PSQL_URL" | sed 's/\/[^/]*$//')

    echo "==> Checking if database '$DB_NAME' exists..."

    # Try to create database (will fail silently if exists)
    psql "$BASE_URL/postgres" -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
        psql "$BASE_URL/postgres" -c "CREATE DATABASE \"$DB_NAME\"" 2>/dev/null || \
        echo "    Database already exists or cannot be created (may need manual creation)"
fi

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Starting application..."
exec "$@"
