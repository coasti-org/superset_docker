# syntax=docker/dockerfile:1.7
# Multi-target build:
#   - base:   shared layers (OS deps, python deps, entrypoints, translations)
#   - app:    web server / init / beat image (NO browser, several 100 MB smaller)
#   - worker: app + Playwright/Chromium for Alerts & Reports screenshots
#
# Build examples:
#   docker build --target app    -t superset_docker:app    -f docker/Dockerfile .
#   docker build --target worker -t superset_docker:worker -f docker/Dockerfile .
#
# see https://superset.apache.org/docs/installation/docker-builds/#building-your-own-production-docker-image

# Keep in sync with VERSION (CI derives this from the part after "+superset.").
ARG SUPERSET_VERSION=6.1.0
# Translations are versioned per superset minor; bump together with SUPERSET_VERSION.
ARG TRANSLATIONS_DIR=6.0.0

# ---------------------------------------------------------------------------- #
#                                     base                                     #
# ---------------------------------------------------------------------------- #
FROM apache/superset:${SUPERSET_VERSION} AS base
ARG TRANSLATIONS_DIR

# Switching to root to install the required packages
USER root

# NOTE: build-essential/libpq-dev were dropped: psycopg2-binary ships a bundled
# libpq, so nothing here needs a compiler. If you ever add a source-built
# driver, compile it in a separate builder stage and COPY the wheel in,
# instead of shipping the toolchain in the runtime image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    # needed for db wait / debugging (pg_isready, psql)
    postgresql-client \
    # needed for redis wait / debugging
    redis-tools \
    # when used with custom cas:
    ca-certificates \
    # unzip utility
    unzip \
    zip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create necessary directories for Keycloak auth
RUN install -d -o superset -g superset /app/superset/auth_keycloak

# Install additional Python packages into the Superset virtualenv.
# The venv does not include pip, so use uv.
# All versions are pinned in requirements.txt (regenerate via `uv pip compile`).
# COPY-ing the file first means this layer is only rebuilt when deps change.
COPY ./docker/requirements.txt /tmp/requirements.txt
ENV UV_CACHE_DIR=/root/.cache/uv
RUN --mount=type=cache,target=/root/.cache/uv \
    . /app/.venv/bin/activate && \
    uv pip install -r /tmp/requirements.txt

# Fix: superset/views/base.py->get_default_spinner_svg() loads this from the
# frontend source tree, but the production Docker image strips the source after
# building. Provide the file where the code expects it.
# NOTE: Seems like a regression in 6.0.0+
# Have not found a related issue yet.
COPY --chown=superset:superset ./assets/loading.svg /app/superset-frontend/packages/superset-ui-core/src/components/assets/images/loading.svg

# Switch back to superset user
USER superset

# Create necessary directories
RUN mkdir -p /app/superset_home/logs /app/superset_home/celery

# Copy entrypoint scripts
COPY --chown=superset:superset --chmod=755 ./docker/entrypoint/*.sh /app/superset/entrypoint/

# Copy pre-build translations (the . at the end of the source is needed to merge)
# see https://github.com/apache/superset/issues/35959#issuecomment-3481035646
COPY --chown=superset:superset ./translations/${TRANSLATIONS_DIR}/. /app/superset/translations/

# Copy custom modules into pythonpath so they're auto-discovered
COPY --chown=superset:superset ./modules/*.py /app/pythonpath/

# Set some default environment
ENV PYTHONPATH="/app/pythonpath:$PYTHONPATH"
ENV SUPERSET_CONFIG_PATH="/app/superset/superset_config.py"

# NOTE: the former EXTRA_GIDS build-arg was removed. Baking host-specific GIDs
# into a published image ties it to one machine; use runtime `group_add:` in
# docker-compose instead (see docker-compose-sample.yml).

# ---------------------------------------------------------------------------- #
#                          app (web server, init, beat)                        #
# ---------------------------------------------------------------------------- #
FROM base AS app

# Default command (can be overridden in docker-compose)
CMD ["/app/superset/entrypoint/start_superset.sh"]

# ---------------------------------------------------------------------------- #
#                    worker (adds Playwright + Chromium)                       #
# ---------------------------------------------------------------------------- #
FROM base AS worker

USER root

# Playwright caching
RUN install -d -o superset -g superset /app/superset_home/.cache/dconf

ENV PLAYWRIGHT_BROWSERS_PATH=/usr/local/share/playwright-browsers

# playwright itself is already installed (pinned) via requirements.txt in base;
# here we only pull in the browser + its system deps.
RUN . /app/.venv/bin/activate && \
    playwright install-deps chromium && \
    playwright install chromium && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

USER superset

CMD ["/app/superset/entrypoint/start_celery_worker.sh"]