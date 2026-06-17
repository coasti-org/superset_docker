#!/bin/bash
set -e

echo "=============================================="
echo "Initializing Superset Database"
echo "=============================================="

export FLASK_APP=superset

# Wait for database to be ready
echo "Waiting for database to be ready..."
# Note: This script runs in a container of the stack, accessing another container.
# Container-to container communication uses the native ports (not the ones exposed to the host!)
while ! pg_isready -h "${POSTGRES_HOST:-postgres}" -p 5432 -U "${POSTGRES_USER:-superset}" -d "${POSTGRES_DB:-superset}" > /dev/null 2>&1; do
    echo "Database not ready, waiting 5 seconds..."
    sleep 5
done
echo "Database is ready!"

echo "START: Applying DB migrations"
superset db upgrade
echo "COMPLETE: Applying DB migrations"

echo "START: Setting up admin user ( $SUPERSET_ADMIN )"
superset fab create-admin \
            --username "${SUPERSET_ADMIN}" \
            --firstname "Superset" \
            --lastname "Admin" \
            --email "${SUPERSET_ADMIN_EMAIL}" \
            --password "${SUPERSET_PASSWORD}"
echo "COMPLETED: Setting up admin user"

echo "START: Setting up roles and perms"
superset init
echo "COMPLETE: Setting up roles and perms"

if [ "$SUPERSET_LOAD_EXAMPLES" = "yes" ]; then
    # Load some data to play with
    echo "START: Loading examples"
    superset load_examples
    echo "COMPLETE: Loading examples"
fi

echo "=============================================="
echo "Database initialization completed successfully"
echo "=============================================="
