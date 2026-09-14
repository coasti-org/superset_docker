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
- Keycloak `auth_role_mappings` in `keycloak_clients.yml` changed direction:
  it is now `KeycloakRole: SupersetRole` (was documented as the reverse).
  Existing files must be flipped or users get the wrong roles at the next
  login — see step 9 in `UPGRADING.md`.
  
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
- Keycloak: `keycloak_clients.yml` is re-read when it changes (cached by file
  mtime), so `auth_role_mappings` and `role_based_redirections` edits apply on
  the next login/request without a container restart. Connection settings
  (`host`, `realm`, `client_id`, `client_secret`) still require a restart.
### Changed
 
- Redis now only evicts keys that have a TTL (`volatile-lru`, was
  `allkeys-lru`). This protects queued Celery tasks (reports/alerts) from
  being silently dropped when memory is low. If Redis still runs out of
  space, it will now reject writes with an error instead — raise
  `REDIS_MAXMEMORY` if that happens.
- Redis databases were reorganized so each consumer gets its own DB number,
  fixing two collisions (explore form data vs. the Celery broker, and
  distributed coordination vs. the thumbnail cache). All affected data is
  transient, so no migration is needed.
- Celery workers now prefetch only 1 task at a time instead of 10
  (`worker_prefetch_multiplier`), so long-running report tasks don't hog the
  queue and a crash no longer requeues a large batch at once.
- Logging moved from files in `logs/` to stdout/stderr, with rotation handled
  by Docker's own logging driver (json-file, 20m x 5 files).
- gunicorn's request line/header size limits are now finite (but generous)
  instead of unlimited.
- Services start up faster and with fewer dependencies: the app no longer
  waits for Caddy, and worker/beat no longer wait for the app.
- Entrypoint wait loops now time out after 3 minutes instead of waiting
  forever, and use `REDISCLI_AUTH` so the Redis password no longer shows up
  in `ps` output.
- Infra images are pinned to specific minor versions (postgres:17.5,
  redis:7.4, caddy:2.10).
- The Dockerfile's base image version is now derived from the `VERSION` file
  by CI, so the two can't drift apart.
- Removed from the image to reduce its size: the build toolchain
  (`build-essential`, `libpq-dev`), source-built `psycopg2` (the pinned
  `-binary` wheel remains), and unused `gevent`, `libaio1`, `wget`.
- CI: the `latest` and `stable` tags now only move on real releases (before,
  `test-*` builds could also move `latest`); the base image is now always
  freshly pulled.
### Fixed
 
- `SERVER_WORKER_AMOUNT` / `SERVER_THREADS_AMOUNT` are now actually applied;
  gunicorn previously ran a hardcoded 4 workers and ignored both vars.
- `superset-init` is idempotent: re-running the stack no longer trips over the
  already-existing admin user.
- `superset-beat` removes a stale pidfile from unclean shutdowns instead of
  refusing to start.
- CRLF normalization moved fully to `.gitattributes`; removed the redundant
  `sed` from the Dockerfile.
- Keycloak role mapping actually works: `oauth_user_info` no longer pre-maps
  realm roles before handing them to Flask-AppBuilder's role sync (the value
  was mapped twice and could resolve to no Superset role at all). It now
  returns the raw realm roles and lets `AUTH_ROLES_MAPPING` do the lookup.
- `load_user_jwt` no longer raises `AttributeError` on an unknown username;
  the `None` user is rejected before `is_active` is read. Keycloak log lines
  are prefixed with the username.
- The image no longer downgrades `pillow` to 10.3.0 (superset 6.1.0 pins
  11.3.0). `docker/requirements.txt` only lists packages the base image does
  not already ship, so superset's own pins for `celery`, `redis`,
  `itsdangerous` and `pillow` are left intact.

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
