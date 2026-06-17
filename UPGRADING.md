# Upgrading Guide

Use this file as a single checklist and update tracking log.

Version format: `<wrapper_version>+superset.<superset_version>` — example: `0.1.2+superset.6.0.0`

- Wrapper version: changes in this repository (compose files, scripts, docs, templates, modules)
- Superset version: upstream Apache Superset version

---

## 1. Update Execution (For Operators / Implementers)

### 1.1 Pre-Update & Backup
- [ ] Notify users about the maintenance window
- [ ] Create a backup of the Superset metadata database (PostgreSQL/MySQL)
- [ ] (Optional) Backup persistent Docker volumes if local storage is used

### 1.2 Execution Steps
- [ ] Fetch the latest git release
- [ ] Check this file for update instructions
- [ ] Stop the running containers:
```bash
  docker compose down
```
- [ ] Modify the superset_config.py if needed (or anything else mentioned in the instructions)
- [ ] Pull the new Docker image:
```bash
  docker compose pull
```
- [ ] Start the environment in detached mode:
```bash
  docker compose up -d
```

### 1.3 Post-Update Smoke Test (Quick Validation)
- [ ] Verify all containers are running properly (docker compose ps)
- [ ] Log in to the UI successfully
- [ ] Open a core dashboard and verify all charts load without errors
- [ ] Execute a test query in SQL Lab

## 2. Update Records & Changelog

### 2.1 Update Record Template

Copy this template and append it to the top of the Update Records history when planning or executing an update.
```markdown
## <from_version> -> <to_version>

Date:

### Scope
- [ ] Superset version changed
- [ ] Wrapper version changed

### Backend
- no changes

### Frontend (Charts, Dashboards, etc.)
- no changes

### Notes
-
```

## 3. Developer Instructions & Upgrade Checks (For Developers)

> [!NOTE]  
> This section is intended for developers preparing, testing, and validating a new update in the repository before releasing it to operators.

### 3.2 Baseline Checks (Pre-Release Validation)

- [ ] Create update record (append to Update Records below)
- [ ] Define target version and maintenance window
- [ ] Confirm target version string in `VERSION`
- [ ] Validate docker startup
- [ ] Validate login
- [ ] Validate dashboard load
- [ ] Validate SQL Lab query execution
- [ ] Validate alerts/reports flow
- [ ] Mark update record as done

### 3.3 Superset Delta Checks (If Superset Version Changed)

- [ ] Read upstream apache/superset UPDATING.md for target version
- [ ] Review upstream breaking changes and deprecations
- [ ] Review cache/config changes
- [ ] Review feature flag removals/renames
- [ ] Review docker/runtime changes
- [ ] Update `config/superset_config_sample.py` if required
- [ ] Update `README.md` and `docs/*` if behavior changed
- [ ] Update `CHANGELOG.md` with Superset upgrade notes
- [ ] Update `VERSION` with new Superset part

### 3.4 coasti Wrapper Delta Checks (If Wrapper Version Changed)

- [ ] Review changed files in `docker/*`, `scripts/*`, `config/*`, `docs/*`, `modules/*`
- [ ] Update docs for changed behavior
- [ ] Run targeted validation based on changed components
- [ ] Update `CHANGELOG.md` with wrapper changes
- [ ] Update `VERSION` with new wrapper part

##  4. Changelog

### *0.1.2+superset.6.0.0 -> 0.1.3+superset.6.1.0*

### Scope
- [x] Superset version changed
- [x] Wrapper version changed

### Backend
- `config/superset_config.py`:
    - add `DISTRIBUTED_COORDINATION_CONFIG` (new in 6.1, recommended for Redis-backed production), see upstream [UPDATING.md 6.1.0 section](https://github.com/apache/superset/blob/6.1.0/UPDATING.md).
    - removed obsolet `TABLE_NAMES_CACHE_CONFIG` (renamed to DATA_CACHE_CONFIG since Superset 1.0)

### Frontend (Charts, Dashboards, etc.)
- no changes

### Notes
--
---
