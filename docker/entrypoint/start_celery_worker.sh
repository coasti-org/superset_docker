#!/bin/bash
set -euo pipefail

echo "=============================================="
echo "Starting Celery Worker"
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

echo "Starting Celery Worker..."
# Logs go to stdout (no --logfile) so `docker logs` works and rotation is
# handled by the logging driver.
exec celery --app=superset.tasks.celery_app:app worker \
    --pool=prefork \
    --concurrency="${CELERY_WORKER_CONCURRENCY:-4}" \
    --optimization=fair \
    --loglevel="${LOG_LEVEL:-INFO}"