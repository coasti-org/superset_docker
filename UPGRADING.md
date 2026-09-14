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

### *0.1.4+superset.6.1.0 -> 0.2.0+superset.6.1.0*

Date: 2026-07-22

### Scope
- [ ] Superset version changed
- [x] Wrapper version changed (breaking — read before updating!)

### Required migration steps (in order)

1. **Release ordering (developers):** push the `0.2.0+superset.6.1.0` git tag
   and let CI publish the images *before* deploying anywhere — the new compose
   file references both `0.2.0-superset.6.1.0` and `0.2.0-superset.6.1.0-worker`,
   which do not exist until CI has built them.

2. **Re-copy the config and compose files.** Both changed structurally:
```bash
   cp ./config/.env.jinja ./config/.env            # then re-fill your values!
   cp ./config/superset_config_sample.py ./config/superset_config.py  # re-apply local edits
   cp ./docker/docker-compose-sample.yml ./docker/docker-compose.yml
```

3. **`.env`: verify required secrets are set.** The stack now fails fast if
   `SUPERSET_SECRET_KEY`, `SUPERSET_PASSWORD`, `POSTGRES_PASSWORD` or
   `REDIS_PASSWORD` are unset — there are no insecure fallbacks anymore.
   Keep your *existing* values (especially `SUPERSET_SECRET_KEY` and
   `POSTGRES_PASSWORD`), otherwise sessions and DB access break.

4. **`.env`: pick a resource profile.** Defaults now target a production
   machine (4 CPU / 16GB RAM). On a small host (2 vCPU / 4GB RAM), uncomment
   the **tight profile** blocks — both the concurrency block (workers/threads/
   celery) *and* the memory block. Do not mix profiles.

5. **DuckDB connections (if used):** in every DuckDB database connection
   (Advanced -> Engine Parameters), set an explicit memory cap — DuckDB now
   runs inside memory-limited containers and otherwise sizes itself to host
   RAM and gets OOM-killed:
```json
   {"connect_args": {"config": {"memory_limit": "512MB", "threads": 2,
     "temp_directory": "/app/superset_home/duckdb_tmp"}, "read_only": true}}
```
   (Tight profile: `"memory_limit": "256MB", "threads": 1`.)

6. **Update host-side tooling that references container names.** Fixed
   `container_name`s were removed; containers are now named by compose
   (`superset-app-1`, ...). Replace `docker exec/logs/restart superset-app`
   with `docker compose ... exec/logs/restart superset-app` in cron jobs,
   backup scripts, and monitoring. Check `scripts/backup.sh` and
   `scripts/reset_cache.sh` in your deployment.

7. **Replace `reset_cache.sh` with the version shipped in this release.** The
   old script used `FLUSHALL` (now wipes queued reports/alerts, since the
   Redis instance also holds the celery broker) and fixed container names.
   The new script flushes only the cache DBs (`1`-`6`, `8`), works via
   `docker compose`, and no longer restarts services by default — pass
   `--restart` in your cron line if you want to keep the nightly recycle.

8. **Port access:** Superset is no longer published on host port `8088`; all
   access goes through Caddy at `https://<DOMAIN_NAME>`. Anything that hit
   `http://<host>:8088` directly (health monitors, io-tools, bookmarks) must
   switch to the Caddy endpoint or use the commented loopback binding.

9. **Keycloak: flip `auth_role_mappings` in `keycloak_clients.yml`.** The
   mapping direction was documented and implemented backwards. It is now
   **`KeycloakRole: SupersetRole`** (left = Keycloak, right = Superset), which
   is the shape Flask-AppBuilder's `AUTH_ROLES_MAPPING` actually expects.
   Because `AUTH_ROLES_SYNC_AT_LOGIN` is enabled for Keycloak deployments, an
   un-flipped file resolves to the wrong roles on the *next login* — users can
   end up with `AUTH_USER_REGISTRATION_ROLE` (`Public`) instead of their real
   role. Edit the file before restarting:
```yaml
   # before (0.1.x)            # after (0.2.0)
   auth_role_mappings:         auth_role_mappings:
     Admin: superset_admin       superset_admin: Admin
     Alpha: superset_alpha       superset_alpha: Alpha
     Gamma: superset_gamma       superset_gamma: Gamma
```
   A Keycloak role may map to several Superset roles by using a list on the
   right (`superset_admin: [Admin, Alpha]`). `role_based_redirections` is
   unaffected — it was already keyed by Superset role name.
   Verify after the update: log in with a test user per role and check
   Settings -> List Users, or watch `docker compose logs superset-app` for the
   `AUTH_ROLES_MAPPING resolved to:` line (needs `LOG_LEVEL=DEBUG`).

### Backend
- `docker-compose`: two image flavors (`<version>` and `<version>-worker`);
  worker/beat/app dependency graph loosened; memory limits on all services;
  logs to stdout with docker-side rotation; postgres/redis/caddy pinned to
  minor versions.
- Redis: eviction policy `allkeys-lru` -> `volatile-lru` (queued celery tasks
  can no longer be evicted). DB layout: explore form data db 0 -> 6, celery
  result backend db 0 -> 10, distributed coordination db 1 -> 9. All moved DBs
  hold transient data — no migration needed, but in-flight async queries and
  unfinished report runs at the moment of the update are lost (do the update
  in a maintenance window as usual).
- `superset_config.py`: `worker_prefetch_multiplier` 10 -> 1; log level via
  `LOG_LEVEL` env (default INFO, was DEBUG); gunicorn timeout raised to 180
  to match `SUPERSET_WEBSERVER_TIMEOUT`.
- Entrypoints: gunicorn now honors `SERVER_WORKER_AMOUNT` /
  `SERVER_THREADS_AMOUNT` (previously hardcoded 4 workers). If you relied on
  the hardcoded value while your `.env` said something else, your worker count
  changes now.
- init is idempotent; repeated `up` no longer trips over the existing admin.
- Keycloak (`modules/KeycloakSecurityManager.py`): `auth_role_mappings` is now
  read in the correct direction (`KeycloakRole: SupersetRole`) and handed to
  Flask-AppBuilder's own role sync instead of being pre-mapped in
  `oauth_user_info` (which double-mapped and could resolve to no role at all).
  See migration step 9 — this requires an edit to `keycloak_clients.yml`.
- Keycloak: `keycloak_clients.yml` is re-read on change (cached by file mtime),
  so `auth_role_mappings` and `role_based_redirections` edits take effect on
  the next login / request without restarting the container. The connection
  settings (`host`, `realm`, `client_id`, `client_secret`) are still read once
  at startup and *do* need a restart.

### Frontend (Charts, Dashboards, etc.)
- no changes

### Notes
- Wrapper-only release: the Superset version stays 6.1.0, so no metadata DB
  migration beyond the usual `superset db upgrade` no-op.
- Existing volumes (`postgres_data`, `redis_data`, `superset_home`) are kept
  and compatible; nothing is renamed.
- Keycloak deployments: no metadata changes, but user role assignments are
  re-synced at the next login from `auth_role_mappings`. Do step 9 *before*
  `docker compose up -d`, or the first logins will overwrite correct role
  assignments with wrong ones.


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