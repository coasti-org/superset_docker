#!/bin/bash
set -e

echo "=============================================="
echo "Starting Celery Worker"
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
CELERY_DIR="/app/superset_home/celery"
mkdir -p "${LOG_DIR}" "${CELERY_DIR}"

echo "Starting Celery Worker..."
exec celery --app=superset.tasks.celery_app:app worker \
    --pool=prefork \
    --concurrency=4 \
    --optimization=fair \
    --logfile="${LOG_DIR}/celery_worker.log" \
    --loglevel=INFO
