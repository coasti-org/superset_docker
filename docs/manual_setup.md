# Manual Setup

Instead of using copier, you can manually follow these steps:


```bash
# Clone the repo
git clone git@github.com:linkFISH-Consulting/superset_docker.git
cd superset_docker

# Copy Docker Compose template
cp ./docker/docker-compose-sample.yml ./docker/docker-compose.yml

# Copy environment template
cp ./config/.env.jinja ./config/.env

# Edit .env with your secure passwords
nano .env  # or use your preferred editor

# Copy Superset configuration template
cp ./config/superset_config_sample.py ./config/superset_config.py

# Optional: Edit superset_config.py for custom settings (e.g., EXTRA_CATEGORICAL_COLOR_SCHEMES)
nano ./config/superset_config.py

# Copy Keycloak client template when using AUTH_TYPE=AUTH_OAUTH
cp ./config/keycloak_clients.sample.yml ./config/keycloak_clients.yml
```

Only copy [config/keycloak_clients.yml](config/keycloak_clients.yml) if you plan to enable Keycloak via `AUTH_TYPE=AUTH_OAUTH`; leave it untouched for the default database login. After copying, update the file with your Keycloak host/realm/client values and flip `AUTH_TYPE` in `.env` from `AUTH_DB` to `AUTH_OAUTH`.


See below for configuration.

**Important**: Change these values in `.env`:
- `POSTGRES_PASSWORD`: Strong password for PostgreSQL
- `REDIS_PASSWORD`: Strong password for Redis
- `SUPERSET_PASSWORD`: Admin user password
- `SUPERSET_SECRET_KEY`: Generate with `openssl rand -base64 42`
- `AUTH_TYPE`: Keep `AUTH_DB` for Superset's login form. Switch to `AUTH_OAUTH` only after configuring Keycloak and updating [config/keycloak_clients.yml](config/keycloak_clients.yml).
