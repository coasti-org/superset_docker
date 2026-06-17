#!/bin/bash
set -e

# Default to restrictive permissions for any newly created files.
# (On some Windows-mounted filesystems, chmod may be a no-op.)
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
DOCKER_PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

# Allow override via env var(s)
ENV_FILE="${SUPERSET_ENV_FILE:-${DOCKER_PROJECT_ROOT}/config/.env}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-superset}"
COMPOSE_FILE_PATH="${DOCKER_PROJECT_ROOT}/docker-compose.yml"

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
        if [ -n "$COMPOSE_FILE_PATH" ]; then
            compose_bin -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE_PATH" "$@"
        else
            compose_bin -p "$COMPOSE_PROJECT_NAME" "$@"
        fi
    )
}

echo "=============================================="
echo "Superset Backup Script"
echo "=============================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Create backup directory with timestamp
BACKUP_DIR="${DOCKER_PROJECT_ROOT}/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR" 2>/dev/null || true

print_status "Creating backup in: $BACKUP_DIR"

# Source environment variables
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
else
    print_warning ".env file not found at '$ENV_FILE', using default values"
    POSTGRES_USER=${POSTGRES_USER:-superset}
    POSTGRES_DB=${POSTGRES_DB:-superset}
fi

# Backup PostgreSQL database
print_status "Backing up PostgreSQL database..."
compose exec -T superset-postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_DIR/postgres_backup.sql.gz"

# Backup Redis data
print_status "Backing up Redis data..."
compose exec -T superset-redis redis-cli --no-auth-warning -a "$REDIS_PASSWORD" BGSAVE
sleep 5
docker cp "$(compose ps -q superset-redis)":/data/dump.rdb "$BACKUP_DIR/redis_dump.rdb"

# Backup Docker volumes
print_status "Backing up Superset home directory (may take a while)..."
SUPERSET_HOME_VOLUME="${COMPOSE_PROJECT_NAME}_superset_home"
if ! docker volume inspect "$SUPERSET_HOME_VOLUME" >/dev/null 2>&1; then
    print_warning "Docker volume '$SUPERSET_HOME_VOLUME' not found; backup may be empty if the volume name is different."
fi
docker run --rm -v "${SUPERSET_HOME_VOLUME}":/data -v "$BACKUP_DIR":/backup alpine sh -c 'tar czf /backup/superset_home.tar.gz -C /data . && ls -lh /backup/superset_home.tar.gz'

# Backup configuration files
print_status "Backing up configuration files..."
if [ -f "$ENV_FILE" ]; then
    # Avoid copying permissions from the source .env; write a new file with restrictive mode.
    ( umask 077; cat "$ENV_FILE" > "$BACKUP_DIR/env_backup" )
    chmod 600 "$BACKUP_DIR/env_backup" 2>/dev/null || true
fi
if [ -n "$COMPOSE_FILE_PATH" ] && [ -f "$COMPOSE_FILE_PATH" ]; then
    cp "$COMPOSE_FILE_PATH" "$BACKUP_DIR/docker-compose.yml"
fi
cp -r "${DOCKER_PROJECT_ROOT}/docker" "$BACKUP_DIR/" 2>/dev/null || true

# Create restore script
cat > "$BACKUP_DIR/restore.sh" << EOF
#!/bin/bash
set -e

SCRIPT_DIR="\$(cd -- "\$(dirname -- "\${BASH_SOURCE[0]}")" && pwd -P)"
cd -- "\$SCRIPT_DIR"

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}"
ORIGINAL_PROJECT_ROOT="${DOCKER_PROJECT_ROOT}"
ORIGINAL_COMPOSE_FILE_PATH="${COMPOSE_FILE_PATH}"
ENV_FILE="\${SUPERSET_ENV_FILE:-\${SCRIPT_DIR}/env_backup}"

if docker compose version >/dev/null 2>&1; then
    compose_bin() { docker compose "\$@"; }
elif command -v docker-compose >/dev/null 2>&1; then
    compose_bin() { docker-compose "\$@"; }
else
    echo "ERROR: Neither 'docker compose' nor 'docker-compose' was found in PATH." >&2
    exit 1
fi

compose() {
    (
        cd -- "\$ORIGINAL_PROJECT_ROOT"
        COMPOSE_FILE_PATH="\${COMPOSE_FILE:-\$ORIGINAL_COMPOSE_FILE_PATH}"
        if [ -n "\$COMPOSE_FILE_PATH" ]; then
            compose_bin -p "$COMPOSE_PROJECT_NAME" -f "\$COMPOSE_FILE_PATH" "\$@"
        else
            compose_bin -p "$COMPOSE_PROJECT_NAME" "\$@"
        fi
    )
}

echo "Restoring Superset from backup..."

if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "WARNING: env file not found at '$ENV_FILE' (continuing with defaults)" >&2
fi

POSTGRES_USER=${POSTGRES_USER:-superset}
POSTGRES_DB=${POSTGRES_DB:-superset}

# Stop services
echo "Stopping containers..."
compose down
compose up -d superset-postgres
sleep 10

# Drop and recreate the database
echo "Clearing existing PostgreSQL data..."
compose exec -T superset-postgres psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
compose exec -T superset-postgres psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB;"

echo "Restoring PostgreSQL database..."
gunzip -c postgres_backup.sql.gz | compose exec -T superset-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
echo "PostgreSQL database restored."

# Restore Redis
echo "Restoring Redis data..."
compose up -d superset-redis
REDIS_CID="\$(compose ps -q superset-redis)"
if [ -z "\$REDIS_CID" ]; then
    echo "ERROR: Could not determine Redis container id." >&2
    exit 1
fi
docker cp redis_dump.rdb "\${REDIS_CID}:/data/dump.rdb"
compose restart superset-redis
echo "Redis data restored."

# Restore Superset home (not enabled by default since it may contain large files and is not strictly necessary for a functional restore)
# echo "Restoring Superset home directory..."
# if [ ! -f "\$SCRIPT_DIR/superset_home.tar.gz" ]; then
#     echo "ERROR: Missing superset_home.tar.gz in backup folder: \$SCRIPT_DIR" >&2
#     exit 1
# fi
# docker run --rm -v "${COMPOSE_PROJECT_NAME}_superset_home":/data -v "\$SCRIPT_DIR":/backup alpine tar xzf /backup/superset_home.tar.gz -C /data
# echo "Superset home directory volume restored."

echo "Starting all services..."
compose up -d

echo "Restore completed"
EOF

chmod +x "$BACKUP_DIR/restore.sh"

print_status "Backup completed successfully!"
print_status "Backup location: $BACKUP_DIR"
print_status "To restore, run: cd $BACKUP_DIR && ./restore.sh"
