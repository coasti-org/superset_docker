# Migration Guide

This guide covers migrating an existing Superset instance to this Docker stack.

## From Bare Metal to Docker Stack

### Prerequisites
- Ensure Docker and Docker Compose are installed.
- Back up all data before starting.

### Step 1: Backup Existing Data

1. **Superset Configuration**:
   - Copy `superset_config.py` to a safe location (e.g., `./backup/superset_config.py`).

2. **Environment Variables**:
   - Copy `.env` or export environment variables to a file.

3. **Redis Database** (if needed):
   - If Redis contains persistent data (e.g., custom caches), back it up.
   - Command: `redis-cli --rdb /path/to/backup.rdb`

4. **PostgreSQL Database**:
   - Back up the Superset metadata database.
   - Command: `pg_dump -U superset -h localhost superset > superset_backup.sql`

### Step 2: Set Up Docker Stack

Follow the setup instructions in [README.md](README.md).

### Step 3: Restore Data

**Important**: Restore your existing database to `superset-postgres` **before** running `superset-app`.

1. **Database**:
   - Start only PostgreSQL: `docker compose up -d superset-postgres`
   - Wait for it to be ready: `sleep 10`
   - Restore the backup: `gunzip -c your-backup.sql.gz | docker compose exec -T superset-postgres psql -U superset -d superset`

2. **Configuration**:
   - Update `config/superset_config.py` with your backed-up settings, adapting for Docker (e.g., change hosts to service names like `postgres`).
   - **Variables to Migrate**:
     - `EXTRA_CATEGORICAL_COLOR_SCHEMES`: Copy from old `superset_config.py`.
     - `APP_NAME`, `APP_ICON`, `MAPBOX_API_KEY`, `THUMBNAIL_SELENIUM_USER`: Set in `superset_config`.
     - `SMTP_*`: Set in `.env`.
   - **SUPERSET_SECRET_KEY**: Reuse the same key via `.env`, or generate a new one and run `superset re-encrypt-secrets` with `PREVIOUS_SECRET_KEY` set once.

3. **Assets and Customizations**:
   - Copy custom images from the previous path to `./assets/images/`. They will be accessible via `/static/assets/custom/images/`.
   - Restore any custom modules or translations.

4. **Custom CA**:
   - See [README.md](README.md) for `REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE` setup.

5. **Keycloak**:
   - See [README.md](README.md) for OAuth integration steps.

### Step 4: Migrate Content

- Use Superset's export/import feature for dashboards, charts, and datasets.
- Export from the old instance and import into the new one via the web UI.

### Step 5: Test and Go Live

- Start the stack: `docker compose up -d`
- Verify functionality, especially database connections and authentication.
- Update DNS/reverse proxy to point to the new instance.

## Version Migrations

For upgrading between Superset versions within this stack, refer to [CHANGELOG.md](CHANGELOG.md) for breaking changes, migration steps, and compatibility notes. Always back up before upgrading.
