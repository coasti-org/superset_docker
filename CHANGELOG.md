# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

TLDR:
- Bugfixes 0.0.1 (Revision)
- Features 0.1.0 (Minor Version)
- Breaking Changes 1.0.0 (Major Version)

We keep track of the superset version (first part) and our wrapping for coasti (second part, pre-release notation)

## Upcoming


### Dev

- Removed auto-release workflow, because we were not using it.


## 0.2.0+superset.6.1.0 - 2026-07-22

Minor bump (not a revision): this release contains breaking changes to the
compose stack and `.env` layout. See "Breaking" below and `UPGRADING.md`
before updating an existing deployment.

### Breaking
 
- Two image flavors are published: `<version>` (app: web server, init, beat)
  and `<version>-worker` (adds Playwright/Chromium for report screenshots).
  The compose file references both.
- Removed `container_name` from all services to support `--scale` and multiple
  stacks per host. Container names change (e.g. `superset-app` ->
  `superset-app-1`); service DNS names are unchanged.
- Superset is no longer published on host port 8088; all access goes through
  Caddy. A commented loopback binding remains for local debugging.
- Compose now fails fast (`${VAR:?}`) when `SUPERSET_SECRET_KEY`,
  `SUPERSET_PASSWORD`, `POSTGRES_PASSWORD` or `REDIS_PASSWORD` are unset,
  instead of silently falling back to insecure defaults.
- Removed the `EXTRA_GIDS` build-arg; grant extra groups at runtime via
  `group_add:` in compose instead of baking host-specific GIDs into the image.
  
### Added
 
- Multi-target Dockerfile (`base` / `app` / `worker`); the app image no longer
  ships a browser and is several hundred MB smaller.
- `docker/requirements.txt` with fully pinned Python dependencies for
  reproducible image builds.
- Memory limits for every service, env-tunable, with a minimal profile summing
  to ~4GB (matching the documented minimum). Roomier profile documented in
  `.env` comments.
- Healthcheck for `superset-beat`.
- `LOG_LEVEL` env var controlling superset + celery log level (default INFO).
- `CELERY_WORKER_CONCURRENCY` and `SUPERSET_WORKER_SHM_SIZE` env vars.
- CI: SBOM and provenance attestations for published images.
### Changed
 
- Redis eviction policy changed from `allkeys-lru` to `volatile-lru`: only
  TTL'd cache keys are evicted, so queued Celery tasks (reports/alerts) can no
  longer be silently dropped under memory pressure. If unevictable keys ever
  fill `maxmemory`, Redis fails writes loudly — raise `REDIS_MAXMEMORY` then.
- Redis DB layout reorganized so every consumer has its own DB: explore form
  data moved db 0 -> 6 (it collided with the Celery broker), celery result
  backend db 0 -> 10, distributed coordination db 1 -> 9 (it collided with the
  thumbnail cache). These hold transient data; no migration needed.
- Celery `worker_prefetch_multiplier` 10 -> 1: long-running report tasks no
  longer hoard the queue, and crashes no longer redeliver large batches.
- All processes log to stdout/stderr; rotation is handled by the Docker
  logging driver (json-file, 20m x 5) instead of unbounded files in `logs/`.
- gunicorn's unlimited request line/header sizes replaced with generous finite
  limits.
- Loosened the compose dependency graph: the app no longer waits on Caddy,
  worker/beat no longer wait on the app. Faster, less coupled startup.
- Entrypoint wait loops are bounded (fail after 3 minutes instead of forever)
  and use `REDISCLI_AUTH`, keeping the Redis password out of `ps` output.
- Infra images pinned to minor versions (postgres:17.5, redis:7.4, caddy:2.10).
- Dockerfile base version is an `ARG` derived by CI from the `VERSION` file,
  so the two can no longer drift apart.
- Dropped from the image: build toolchain (`build-essential`, `libpq-dev`),
  source-built `psycopg2` (the pinned `-binary` wheel remains), unused
  `gevent`, `libaio1`, `wget`.
- CI: `latest` and `stable` tags only move on real releases (previously
  `test-*` tags also moved `latest`); base image digest refreshed via
  `pull: true`.
### Fixed
 
- `SERVER_WORKER_AMOUNT` / `SERVER_THREADS_AMOUNT` are now actually applied;
  gunicorn previously ran a hardcoded 4 workers and ignored both vars.
- `superset-init` is idempotent: re-running the stack no longer trips over the
  already-existing admin user.
- `superset-beat` removes a stale pidfile from unclean shutdowns instead of
  refusing to start.
- CRLF normalization moved fully to `.gitattributes`; removed the redundant
  `sed` from the Dockerfile.

### Dev

- Removed auto-release workflow, because we were not using it.

## 0.1.4+superset.6.1.0 - 2026-06-17

- Workaround: added entry to themes in the sample `superset_config.py` so that a custom `LOGO_TARGET_PATH` is respected.

## 0.1.3+superset.6.1.0 - 2026-05-29

### Added

- `DISTRIBUTED_COORDINATION_CONFIG` for Redis-based pub/sub messaging and distributed locking

### Dependencies

- Upgraded Superset to 6.1.0
- Chore: Updated database backend dependencies (`psycopg2-binary`, `duckdb-engine`, `duckdb`, `pymssql`)

### Fixed

- Fixed regression in superset loading spinner erroring in frontend.

## 0.1.2+superset.6.0.0 - 2026-03-04

### Changed
- The versioning schema has to adhere to PEP440 to work with copier. Now using meta (+) instead of prerelease (-) and to get proper ordering, we made our wrapper version the main one, while the superset version is now the meta field.

### Added
- Mapbox integration


## 6.0.0-coasti.0.1.1 - 2026-02-17

### Fixed

- Dark mode working when using example superset_config.py
- German translations are now included in the docker image

## 6.0.0-coasti.0.1.0 - 2026-02-12

### Added
- Resources needed for installation via [copier](https://copier.readthedocs.io/en/stable/)
- Powershell file for simple .env sourcing with Windows

### Changed
- Reworked file structure, to resemble coasti products more closely
- Dev- and keycloak compose files are now designed to be stacked (supply `-f` multiple times to compose)
- now using Playwright as browser integration for alerts & reports (which is officially supported)
- Superset Containers now have an increased shm size (shared memory) for alerting
- updated superset_config_sample.py to reflect new Superset 6.0 standards for theming

### Fixed
- Alerts & Reports are now working as intended.

### Dependencies

- Upgraded Superset to 6.0.0

## 5.0.0-coasti.0.0.1 - 2026-01-26

### Added
- Workflow: push to github container registry
- Workflow: Auto-Release
- Workflow: Changelog-Reminder

### Changed
- versioning to follow superset versioning standards (we will stay on 5.x for Superset 5.x)
- changed CHROMEDRIVER from 116.0.5845.96 to LATEST (fixed to 144.0.7559.96)

## 0.1.0
- Module für Keycloak-Integration und rollenbasierte Weiterleitung hinzugefügt
- Beispiel Compose-File für Keycloak-Stack integriert
- Logik für custom CA-Integration überarbeitet (siehe README)

## 0.0.1
- Ausgerollt bei Kunden
