#!/bin/bash
set -euo pipefail

echo "=============================================="
echo "Starting Celery Beat Scheduler"
echo "=============================================="

export FLASK_APP=superset
export REDISCLI_AUTH="${REDIS_PASSWORD:-}"

MAX_WAIT_ATTEMPTS="${MAX_WAIT_ATTEMPTS:-36}" # 36 * 5s = 3 minutes

wait_for() {
    local name="$1"; shift
    local attempt=0
    echo "Waiting for ${name} to be ready..."
    until "$@" > /dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ "${attempt}" -ge "${MAX_WAIT_ATTEMPTS}" ]; then
            echo "ERROR: ${name} not ready after ${attempt} attempts, giving up." >&2
            exit 1
        fi
        echo "${name} not ready, waiting 5 seconds..."
        sleep 5
    done
    echo "${name} is ready!"
}

wait_for "database" pg_isready \
    -h "${POSTGRES_HOST:-superset-postgres}" -p "${POSTGRES_PORT:-5432}" \
    -U "${POSTGRES_USER:-superset}" -d "${POSTGRES_DB:-superset}"
wait_for "redis" redis-cli -h "${REDIS_HOST:-superset-redis}" -p "${REDIS_PORT:-6379}" ping

CELERY_DIR="/app/superset_home/celery"
mkdir -p "${CELERY_DIR}"

# Remove a stale pidfile from an unclean shutdown, otherwise beat refuses to start.
rm -f "${CELERY_DIR}/celerybeat.pid"

echo "Starting Celery Beat Scheduler..."
# Logs go to stdout (no --logfile); the pidfile is kept for the healthcheck.
exec celery --app=superset.tasks.celery_app:app beat \
    --schedule="${CELERY_DIR}/celerybeat-schedule" \
    --pidfile="${CELERY_DIR}/celerybeat.pid" \
    --loglevel="${LOG_LEVEL:-INFO}"