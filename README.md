# Apache Superset Production Docker Setup

This directory contains a production-ready Docker Compose setup for Apache Superset with separated containers for better scalability, security, and maintenance.


## 📋 Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available
- Mapbox token for Mapbox card integration:
    - register on mapbox (https://www.mapbox.com/)
    - navigate to Admin > Tokens and create a new token
    - set `MAPBOX_API_KEY` in `./config/.env` after the product is deployed

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

## 🚀 Getting Started

### Using the [coasti installer](https://github.com/linkFISH-Consulting/coasti_installer)

```bash
coasti product add git@github.com:linkFISH-Consulting/superset_docker.git
```

### Using [copier](https://copier.readthedocs.io/en/stable/)

```bash
copier copy git@github.com:linkFISH-Consulting/superset_docker.git /abs/path/to/superset_docker --trust
```

## 🔧 Deployment and Docker Cheat-Sheet

The commands below assume that you made a copy of `./docker/docker-compose-sample.yml` to `./docker/docker-compose.yml`.

```bash
# pull the images
docker compose -f ./docker/docker-compose.yml pull

# start superset (and its required containers)
docker compose -f ./docker/docker-compose.yml --env-file ./config/.env up superset-app

# instead of providing the .env to every compose command, you can source it
set -a; source ./config/.env; set +a

# start all containers and send to background
docker compose -f ./docker/docker-compose.yml up -d

# connect to a running container to explore what is happening
docker exec -it superset-app bash

# view logs for a specific container
docker logs -f superset-app

# restart a container
docker restart superset-app

# stop all containers of the stack
docker compose -f ./docker/docker-compose.yml down

# stop and remove docker volumes
docker compose -f ./docker/docker-compose.yml down -v  # WARNING: This deletes all data
```



## 🆙 Updating

```bash
coasti product update superset_docker

copier update -a /abs/path/to/superset_docker/config/install_answers.yml
```


**Note on Version numbers:**

Our Versioning adheres to [semver](https://semver.org/).
Since we essentially just wrap superset, we include their version as metatag, so it is remains easy to spot which version of superset is included.

E.g. `0.1.2+superset.6.0.0` means superset version 6.0.0, while our wrapping codes are at 0.1.2.
This follows [PEP440](https://peps.python.org/pep-0440/#adding-local-version-identifiers) ([Regex Check](https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions)), which is a bit more restrictive than plain semver, but is required to support updates via copier.




## 📚 Further Reading

- [docs/configuration.md](docs/configuration.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)
- [docs/manual_setup.md](docs/manual_setup.md) (without copier)
- [docs/migration.md](docs/migration.md) (from an existing superset instance)
