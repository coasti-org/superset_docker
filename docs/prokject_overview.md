
# Project Overview

## 🐳 Stack

The stack consists of the following containers:
- **Superset**:
    - `superset-app` Main web application server
    - `superset-worker` Celery background processing
    - `superset-beat` Celery task scheduler
    - `superset-init` Runs once during startup for database initialization and migration
- **Database**
    - `superset-postgres` PostgreSQL, for superset's metadata
- **Caching**
    - `superset-redis` Redis for caching and message broker for celery
- **Reverse Proxy**
    - `superset-caddy` Caddy manages the domain, address, ssl, tls etc

## 📁 Directory Structure

This container is usually installed via `coasti product install` and would reside in `/coasti/tools/superset_docker`. The overall coasti structure is:

```
/coasti/
├── config/
│   ├── secrets/          # Secret files
│   ├── products.yml      # Enabled products
│   ├── tools.yml         # Enabled tools
│   └── [product]/        # Symlinks to product configs
├── products/             # Product-specific files
│   └── [product]/
├── tools/                # Shared tools
│   └── [tool]/
├── data/
│   ├── [product]/        # Symlinks to product data
│   └── [tool]/           # Symlinks to tool data
└── logs/
    ├── [product]/
    └── [tool]/
```

Superset-specific structure under `/coasti/tools/superset_docker`:

```
superset_docker/
├── assets/         # Place for custom frontend assets such as images
├── config/         # All configurations, like .env and superset_config.py
├── docker/         # Container related resources
├── modules/        # Custom modules to extend superset_configy.py
├── data/           # Place datamart output here, mounted into containers
├── logs/           # Runtime logs, mounted into containers
└── scripts/        # Helpers to run on the host, e.g. cache reset
```
