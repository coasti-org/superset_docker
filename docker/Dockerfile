FROM apache/superset:6.1.0
# see https://superset.apache.org/docs/installation/docker-builds/#building-your-own-production-docker-image
# Switching to root to install the required packages
USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    # needed for postgres
    build-essential \
    libpq-dev \
    postgresql-client \
    # needed for redis
    redis-tools \
    # when used with custom cas:
    ca-certificates \
    # unzip utility
    unzip \
    zip \
    libaio1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create necessary directories for Keycloak auth
RUN mkdir -p /app/superset/auth_keycloak
RUN chown superset:superset /app/superset/auth_keycloak

# Playwright caching
RUN mkdir -p /app/superset_home/.cache/dconf
RUN chown superset:superset /app/superset_home/.cache/dconf

# Install additional Python packages into the Superset virtualenv.
# The venv does not include pip, so use uv and target /app/.venv/bin/python.
RUN . /app/.venv/bin/activate && \
    uv pip install \
    gevent \
    redis \
    celery \
    # screenshots packages (Alerts & Reports to generate PDFs of dashboards)
    pillow==10.3.0 \
    # auth packages
    flask-oidc==2.2.2 \
    Flask-OpenID==1.3.1 \
    itsdangerous==2.2.0 \
    # db specific drivers
    psycopg2 \
    psycopg2-binary==2.9.12 \
    duckdb-engine==0.17.0 \
    duckdb==1.5.3 \
    pymssql==2.3.13

ENV PLAYWRIGHT_BROWSERS_PATH=/usr/local/share/playwright-browsers

RUN --mount=type=cache,target=/app/superset_home/.cache/uv \
        uv pip install playwright && \
        playwright install-deps && \
        playwright install chromium

# Give extra groups to the superset user if needed
# TODO: we need this at runtime, so invoke entrypoint as root, and use gosu.
# see lf python dbt stack
ARG EXTRA_GIDS
RUN if [ -n "$EXTRA_GIDS" ]; then \
    for group in $EXTRA_GIDS; do \
        if ! getent group $group > /dev/null 2>&1; then \
            groupadd -g $group superset_group_$group; \
        fi; \
        usermod -a -G $group superset; \
    done; \
    fi

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
COPY --chown=superset:superset ./docker/entrypoint/*.sh /app/superset/entrypoint/

# Copy pre-build translations (the . at the end of the source is needed to merge)
# see https://github.com/apache/superset/issues/35959#issuecomment-3481035646
COPY --chown=superset:superset ./translations/6.0.0/. /app/superset/translations/

# Prep scripts, just for convenience
# Normalize line endings (Windows CRLF -> Unix LF) so shebangs work in Linux containers
RUN sed -i 's/\r$//' /app/superset/entrypoint/*.sh
RUN chmod +x /app/superset/entrypoint/*.sh

# Copy custom modules into pythonpath so they're auto-discovered
COPY --chown=superset:superset ./modules/*.py /app/pythonpath/

# Set some default environment
ENV PYTHONPATH="/app/pythonpath:$PYTHONPATH"
ENV SUPERSET_CONFIG_PATH="/app/superset/superset_config.py"

# Default command (can be overridden in docker-compose)
CMD ["/app/superset/entrypoint/start_superset.sh"]
