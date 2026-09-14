#!/bin/bash
set -euo pipefail

echo "=============================================="
echo "Initializing Superset Database"
echo "=============================================="

export FLASK_APP=superset

# Bounded wait for the database.
# Note: This script runs in a container of the stack, accessing another container.
# Container-to-container communication uses the native ports (not the ones exposed to the host!)
MAX_WAIT_ATTEMPTS="${MAX_WAIT_ATTEMPTS:-36}" # 36 * 5s = 3 minutes
attempt=0
echo "Waiting for database to be ready..."
until pg_isready -h "${POSTGRES_HOST:-superset-postgres}" -p 5432 \
        -U "${POSTGRES_USER:-superset}" -d "${POSTGRES_DB:-superset}" > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "${attempt}" -ge "${MAX_WAIT_ATTEMPTS}" ]; then
        echo "ERROR: database not ready after ${attempt} attempts, giving up." >&2
        exit 1
    fi
    echo "Database not ready, waiting 5 seconds..."
    sleep 5
done
echo "Database is ready!"

echo "START: Applying DB migrations"
superset db upgrade
echo "COMPLETE: Applying DB migrations"

# Idempotent admin creation: this service runs on every `up`, and
# `fab create-admin` is not safe to repeat under `set -e`.
echo "START: Setting up admin user ( $SUPERSET_ADMIN )"
if superset fab list-users 2>/dev/null | grep -q "username:${SUPERSET_ADMIN}"; then
    echo "Admin user '${SUPERSET_ADMIN}' already exists, skipping creation."
else
    superset fab create-admin \
                --username "${SUPERSET_ADMIN}" \
                --firstname "Superset" \
                --lastname "Admin" \
                --email "${SUPERSET_ADMIN_EMAIL}" \
                --password "${SUPERSET_PASSWORD}" \
        || echo "WARNING: create-admin failed (user may already exist), continuing."
fi
echo "COMPLETED: Setting up admin user"

echo "START: Setting up roles and perms"
superset init
echo "COMPLETE: Setting up roles and perms"

if [ "${SUPERSET_LOAD_EXAMPLES:-no}" = "yes" ]; then
    # Load some data to play with
    echo "START: Loading examples"
    superset load_examples
    echo "COMPLETE: Loading examples"
fi

echo "=============================================="
echo "Database initialization completed successfully"
echo "=============================================="