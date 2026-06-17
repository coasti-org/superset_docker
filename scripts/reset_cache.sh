#!/bin/bash

# ------------------------------------------------------------------------------ #
# @Author:        F. Paul Spitzner
# @Created:       2025-12-04 11:02:26
# @Last Modified: 2026-02-10 17:34:29
# ------------------------------------------------------------------------------ #
# to run nightly at 03:00 while maintaining the log:
# crontab -e
# 0 3 * * * /coasti/tools/superset/reset_cache.sh >> /coasti/logs/reset_cache_$(date +\%Y\%m\%d_\%H\%M\%S).log 2>&1
# ------------------------------------------------------------------------------ #

set -e

# Get the directory where this script is located to source .env via relative path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Sourcing .env"
source "$SCRIPT_DIR/../config/.env"

echo "Resetting cache in superset-redis container"
docker exec superset-redis redis-cli -a $REDIS_PASSWORD flushall

echo "Restarting superset docker containers"
docker restart superset-app
docker restart superset-beat
docker restart superset-worker

echo "All done"
