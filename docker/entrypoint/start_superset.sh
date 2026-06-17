#!/bin/bash
set -e

echo "=============================================="
echo "Starting Apache Superset Web Server"
echo "=============================================="

export FLASK_APP=superset

# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-superset}" -d "${POSTGRES_DB:-superset}" > /dev/null 2>&1; do
    echo "Database not ready, waiting 5 seconds..."
    sleep 5
done
echo "Database is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
while ! redis-cli -h "${REDIS_HOST:-redis}" -p "${REDIS_PORT:-6379}" -a "${REDIS_PASSWORD}" ping > /dev/null 2>&1; do
    echo "Redis not ready, waiting 5 seconds..."
    sleep 5
done
echo "Redis is ready!"

# Create log directory
LOG_DIR="/app/superset_home/logs"
mkdir -p "${LOG_DIR}"

echo "Starting Superset Web Server..."
exec gunicorn \
    --bind "0.0.0.0:8088" \
    --access-logfile "${LOG_DIR}/gunicorn_access.log" \
    --error-logfile "${LOG_DIR}/gunicorn_error.log" \
    --worker-class gthread \
    --workers 4 \
    --timeout 120 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --limit-request-line 0 \
    --limit-request-field_size 0 \
    "superset.app:create_app()"
