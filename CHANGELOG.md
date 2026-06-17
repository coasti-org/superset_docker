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

### Fixed

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
