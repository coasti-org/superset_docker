#!/bin/bash
set -euo pipefail

echo "=============================================="
echo "Starting Apache Superset Web Server"
echo "=============================================="

export FLASK_APP=superset
# keep the redis password off the redis-cli command line (visible via `ps` otherwise)
export REDISCLI_AUTH="${REDIS_PASSWORD:-}"

# Bounded wait for dependencies. compose `depends_on: service_healthy` covers
# first start; this loop additionally covers container *restarts* (where
# depends_on conditions are not re-evaluated).
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

echo "Starting Superset Web Server..."
# Logs go to stdout/stderr so `docker logs` works and the logging driver
# handles rotation (file logs in a bind mount grow unbounded).
# Worker/thread counts come from the env (SERVER_WORKER_AMOUNT /
# SERVER_THREADS_AMOUNT) — previously documented but silently ignored.
# GUNICORN_TIMEOUT defaults to 180 to match SUPERSET_WEBSERVER_TIMEOUT in
# superset_config.py (it was 120, killing long queries 60s early).
exec gunicorn \
    --bind "0.0.0.0:8088" \
    --access-logfile - \
    --error-logfile - \
    --worker-class gthread \
    --workers "${SERVER_WORKER_AMOUNT:-4}" \
    --threads "${SERVER_THREADS_AMOUNT:-20}" \
    --timeout "${GUNICORN_TIMEOUT:-180}" \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --limit-request-line 8190 \
    --limit-request-field_size 16380 \
    "superset.app:create_app()"
# NOTE: the former `--limit-request-line 0 --limit-request-field_size 0`
# (unlimited) was replaced by generous finite limits. If a legitimate long URL
# ever hits these, raise the number — don't disable the limit.