#!/bin/bash

# ------------------------------------------------------------------------------ #
# @Author:        F. Paul Spitzner/F. Deutsch
# @Created:       2025-12-04 11:02:26
# @Last Modified: 2026-07-22
# ------------------------------------------------------------------------------ #
# Resets the superset CACHES without touching the celery broker.
#
# IMPORTANT: never use FLUSHALL here. Since 0.2.0 the single Redis instance
# also holds the celery broker (db 0), distributed coordination (db 9) and the
# celery result backend (db 10) — flushing those wipes queued reports/alerts
# and in-flight async queries. We flush only the cache DBs:
#   1 thumbnails, 2 table names, 3 data, 4 metadata, 5 filter state,
#   6 explore form data, 8 SQL Lab results
#
# Usage:
#   ./reset_cache.sh             # flush caches only (no downtime)
#   ./reset_cache.sh --restart   # additionally restart app/worker/beat
#
# to run nightly at 03:00 while maintaining the log:
# crontab -e
# 0 3 * * * /coasti/tools/superset/reset_cache.sh >> /coasti/logs/reset_cache_$(date +\%Y\%m\%d_\%H\%M\%S).log 2>&1
# ------------------------------------------------------------------------------ #

set -euo pipefail

CACHE_DBS=(1 2 3 4 5 6 8)

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
DOCKER_PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

# Allow override via env var(s) — same pattern as backup.sh
ENV_FILE="${SUPERSET_ENV_FILE:-${DOCKER_PROJECT_ROOT}/config/.env}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-superset}"
COMPOSE_FILE_PATH="${SUPERSET_COMPOSE_FILE:-${DOCKER_PROJECT_ROOT}/docker/docker-compose.yml}"

if docker compose version >/dev/null 2>&1; then
    compose_bin() { docker compose "$@"; }
elif command -v docker-compose >/dev/null 2>&1; then
    compose_bin() { docker-compose "$@"; }
else
    echo "ERROR: Neither 'docker compose' nor 'docker-compose' was found in PATH." >&2
    exit 1
fi

compose() {
    (
        cd -- "$DOCKER_PROJECT_ROOT"
        compose_bin -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE_PATH" --env-file "$ENV_FILE" "$@"
    )
}

echo "Sourcing ${ENV_FILE}"
# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a

if [ -z "${REDIS_PASSWORD:-}" ]; then
    echo "ERROR: REDIS_PASSWORD is not set (checked ${ENV_FILE})." >&2
    exit 1
fi

# REDISCLI_AUTH keeps the password out of the process list (vs. redis-cli -a).
# -T: no pseudo-TTY, safe for cron.
flush_db() {
    local db="$1"
    compose exec -T -e REDISCLI_AUTH="$REDIS_PASSWORD" superset-redis \
        redis-cli -n "$db" flushdb
}

echo "Flushing superset cache DBs (${CACHE_DBS[*]}) in the superset-redis service"
for db in "${CACHE_DBS[@]}"; do
    printf 'db %-2s: ' "$db"
    flush_db "$db"
done

# A restart is NOT required for the flush to take effect — all flushed caches
# live in Redis, not in the containers. The flag exists for operators who also
# want a nightly process recycle; note it causes a brief downtime.
if [ "${1:-}" = "--restart" ]; then
    echo "Restarting superset services (--restart given)"
    compose restart superset-app superset-worker superset-beat
fi

echo "All done"