import json
import logging
import os

from celery.schedules import crontab
from flask_appbuilder.security.manager import AUTH_DB, AUTH_OAUTH

# Lazy-loaded custom modules
KEYCLOAK_CUSTOM_SECURITY_MANAGER = None
KEYCLOAK_OAUTH_PROVIDERS = []
# LOGOUT_REDIRECT_URL = None

ROLE_BASED_FAB_INDEX_VIEW_PATH = None
ROLE_REDIRECT_MUTATOR = None
set_role_redirect_rules = None

def configure_keycloak_oauth(*_args, **_kwargs):  # type: ignore[empty-body]
    return None

logger = logging.getLogger()

FEATURE_FLAGS = {
    "ALLOW_ADHOC_SUBQUERY": True,
    "ALLOW_FULL_CSV_EXPORT": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_RBAC": True,
    "DRILL_BY": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
    "ESTIMATE_QUERY_COST": True,
    "HORIZONTAL_FILTER_BAR": True,
    "TAGGING_SYSTEM": True,
    "THUMBNAILS": False,
    # reports
    "ALERT_REPORTS": True,
    "DATE_FORMAT_IN_EMAIL_SUBJECT": True,
    "PLAYWRIGHT_REPORTS_AND_THUMBNAILS": True,
}

# proxy fix (X-Forwarded-For) to avoid problems behind a reverse proxy
ENABLE_PROXY_FIX = True

ENABLE_TIME_ROTATE = True # rotating logs
TIME_ROTATE_LOG_LEVEL = logging.DEBUG

logging.getLogger("superset.stats_logger").setLevel(logging.DEBUG)
logging.getLogger("celery").setLevel(logging.DEBUG)
logging.getLogger("superset.tasks").setLevel(logging.DEBUG)

# to get sqlite working:
PREVENT_UNSAFE_DB_CONNECTIONS=False

# hostname is docker compose service name.
SQLALCHEMY_DATABASE_URI = (
    f"postgresql://{os.environ.get('POSTGRES_USER')}"
    + f":{os.environ.get('POSTGRES_PASSWORD')}"
    + f"@{os.environ.get('POSTGRES_HOST', 'postgres')}"
    + f":{os.environ.get('POSTGRES_PORT', '5432')}"
    + f"/{os.environ.get('POSTGRES_DB', 'superset')}"
)

# Language settings
BABEL_DEFAULT_LOCALE = "de"
BABEL_DEFAULT_TIMEZONE = "Europe/Berlin"

# Specify the languages that your application will support
LANGUAGES = {
    "en": {"flag": "us", "name": "English"},
    "de": {"flag": "de", "name": "Deutsch"},
}

# Override the default d3 locale format
# Default values are equivalent to
D3_FORMAT = {
    "decimal": ",",           # - decimal place string (e.g., ".").
    "thousands": ".",         # - group separator string (e.g., ",").
    "grouping": [3],          # - array of group sizes (e.g., [3]), cycled as needed.
    "currency": ["", "€"]     # - currency prefix/suffix strings (e.g., ["$", ""])
}

# ------------------------------ Redis, Caching ------------------------------ #
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
from cachelib.redis import RedisCache
# 1. Thumbnails cache
THUMBNAIL_CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 24,  # 1 day
    'CACHE_KEY_PREFIX': 'thumbnail',
    'CACHE_REDIS_URL': f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1',
}

# 2. Table names cache
TABLE_NAMES_CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 24,  # 1 day
    'CACHE_KEY_PREFIX': 'table_names',
    'CACHE_REDIS_URL': f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/2',
}

# 3. Data cache
DATA_CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 24,  # 1 day
    'CACHE_KEY_PREFIX': 'data',
    'CACHE_REDIS_URL': f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/3',
}

# 4. Metadata cache
CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 24,  # 1 day
    'CACHE_KEY_PREFIX': 'metadata',
    'CACHE_REDIS_URL': f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/4',
}

# 5. Filter state cache
FILTER_STATE_CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 24,  # 1 day
    'CACHE_KEY_PREFIX': 'filter_state',
    'CACHE_REDIS_URL': f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/5',
}

# 6. Explore chart form data cache
EXPLORE_FORM_DATA_CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 24,  # 1 day
    'CACHE_KEY_PREFIX': 'form_data',
    'CACHE_REDIS_URL': f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0',
}

# New in Superset 6.1: Distributed coordination backend for pub/sub messaging and
# atomic distributed locking. Used by the Global Task Framework (GTF) for abort
# notifications and task completion signaling.
DISTRIBUTED_COORDINATION_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_KEY_PREFIX": "signal_",
    "CACHE_REDIS_URL": f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1",
    "CACHE_DEFAULT_TIMEOUT": 300,
}

# ------------------------- Report Setup, needs Redis ------------------------ #

class CeleryConfig:
    broker_url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"
    imports = (
        "superset.sql_lab",
        "superset.tasks.scheduler",
    )
    result_backend = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"
    worker_prefetch_multiplier = 10
    task_acks_late = True
    task_annotations = {
        "sql_lab.get_sql_results": {
            "rate_limit": "100/s",
        },
    }
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=0, hour=0),
        },
    }


CELERY_CONFIG = CeleryConfig
RESULTS_BACKEND = RedisCache(
    host=f'{REDIS_HOST}', password=f'{REDIS_PASSWORD}', db=8, port=f'{REDIS_PORT}', key_prefix='superset_results'
)

 # ------------------------ ALERTS & REPORTS ------------------------ #

ALERT_REPORTS_NOTIFICATION_DRY_RUN = False
# Slack configuration
# SLACK_API_TOKEN = "xoxb-"

# Email configuration
SMTP_HOST = os.environ.get("SMTP_HOST")  # change to your host
SMTP_PORT = os.environ.get("SMTP_PORT")  # your port, e.g. 587
SMTP_STARTTLS = True
SMTP_SSL_SERVER_AUTH = True  # If you're using an SMTP server with a valid certificate
SMTP_SSL = False
SMTP_USER = os.environ.get(
    "SMTP_USER"  # use the empty string "" if using an unauthenticated SMTP server
)
SMTP_PASSWORD = os.environ.get(
    "SMTP_PASSWORD"  # use the empty string "" if using an unauthenticated SMTP server
)
SMTP_MAIL_FROM = os.environ.get("SMTP_USER")
EMAIL_REPORTS_SUBJECT_PREFIX = (
    "[Superset] "  # optional - overwrites default value in config.py of "[Report] "
)

# WebDriver configuration -> We use Playwright with chromium (officially supported)
# Firefox doesn't work with playwright yet as the superset developers have hard coded playwright.chromium.launch(args=...)
# we don't want to use a native browser due to its massive dependency footprint
WEBDRIVER_TYPE = "playwright"

# This is for internal use, you can keep http
WEBDRIVER_BASEURL = "http://superset-app:8088"

# This is the link sent to the recipient. Change to your domain, e.g. https://superset.mydomain.com
WEBDRIVER_BASEURL_USER_FRIENDLY = os.environ.get("DOMAIN", "http://localhost:8088")

# Screenshot configuration
SCREENSHOT_LOCATE_WAIT = 100
SCREENSHOT_LOAD_WAIT = 600
SUPERSET_WEBSERVER_TIMEOUT = 180
# ------------------------- End ALERTS & REPORTS Setup ------------------------ #

# ------------------------ Keycloak Integration ------------------------ #
# AUTH: Keycloak (optional)
AUTH_TYPE_NAME = os.environ.get("AUTH_TYPE", "AUTH_DB").upper()
USE_KEYCLOAK = AUTH_TYPE_NAME == "AUTH_OAUTH"

AUTH_USER_REGISTRATION = False
AUTH_ROLES_SYNC_AT_LOGIN = False
AUTH_USER_REGISTRATION_ROLE = 'Public'
OAUTH_PROVIDERS = []

# This part is relevant for our superset_io_tool - it needs to know which jwt alg to use.
JWT_ALGORITHM = "HS256"

if USE_KEYCLOAK:
    from KeycloakSecurityManager import (
        CUSTOM_SECURITY_MANAGER as _KEYCLOAK_CUSTOM_SECURITY_MANAGER,
        LOGOUT_REDIRECT_URL as _KEYCLOAK_LOGOUT_REDIRECT_URL,
        OAUTH_PROVIDERS as _KEYCLOAK_OAUTH_PROVIDERS,
        configure_keycloak_oauth as _configure_keycloak_oauth,
        AUTH_ROLES_MAPPING as _KEYCLOAK_AUTH_ROLES_MAPPING,
    )

    KEYCLOAK_CUSTOM_SECURITY_MANAGER = _KEYCLOAK_CUSTOM_SECURITY_MANAGER
    LOGOUT_REDIRECT_URL = _KEYCLOAK_LOGOUT_REDIRECT_URL
    KEYCLOAK_OAUTH_PROVIDERS = _KEYCLOAK_OAUTH_PROVIDERS
    configure_keycloak_oauth = _configure_keycloak_oauth

    AUTH_TYPE = AUTH_OAUTH
    AUTH_USER_REGISTRATION = True
    AUTH_ROLES_SYNC_AT_LOGIN = True
    JWT_ALGORITHM = "RS256"
    OAUTH_PROVIDERS = KEYCLOAK_OAUTH_PROVIDERS
    CUSTOM_SECURITY_MANAGER = KEYCLOAK_CUSTOM_SECURITY_MANAGER
    AUTH_ROLES_MAPPING = _KEYCLOAK_AUTH_ROLES_MAPPING
else:
    AUTH_TYPE = AUTH_DB

# role based redirection, change to True to enable
USE_ROLE_BASED_REDIRECTS = os.environ.get("USE_ROLE_BASED_REDIRECTS", "false").lower() == "true"
# Default redirect target used when no role-specific rule matches.
ROLE_BASED_DEFAULT_TARGET = "/dashboard/list"

if USE_ROLE_BASED_REDIRECTS:
    from RoleBasedRedirector import (
        FAB_INDEX_VIEW_PATH as _CUSTOM_FAB_INDEX_VIEW_PATH,
        FLASK_APP_MUTATOR as _ROLE_REDIRECT_MUTATOR,
        set_role_redirect_rules
    )

    # Load role-based redirects dynamically from keycloak_clients.yml.
    set_role_redirect_rules(ROLE_BASED_DEFAULT_TARGET)
    FAB_INDEX_VIEW = _CUSTOM_FAB_INDEX_VIEW_PATH
    FLASK_APP_MUTATOR = _ROLE_REDIRECT_MUTATOR

# ------------------------ End Keycloak Integration ------------------------ #


# ------------------------ Customizations ------------------------ #

LOGO_TARGET_PATH = "/"  # default path when clicking the logo
# FIXME: Remove once issue is resolved upstream (maybe 6.1.1)
# Upstream theme dict merging currently not working
# https://github.com/apache/superset/issues/40375
from superset.config import THEME_DARK as _UPSTREAM_THEME_DARK
from superset.config import THEME_DEFAULT as _UPSTREAM_THEME_DEFAULT

THEME_DEFAULT = {
    **_UPSTREAM_THEME_DEFAULT,
    "token": {
        **_UPSTREAM_THEME_DEFAULT["token"],
        "brandAppName": "coasti Superset",  # Window titles
        "brandLogoAlt": "Apache Superset powered by coasti",  # Logo alt text
        "brandLogoUrl": "/static/assets/custom/images/coasti_logo.png",
        "brandLogoHref": LOGO_TARGET_PATH or "/",
    },
}
THEME_DARK = {
    **_UPSTREAM_THEME_DARK,
    "algorithm": "dark",  # needed, otherwise we break default dark style
    "token": {
        **_UPSTREAM_THEME_DARK["token"],
        "brandAppName": "coasti Superset",  # Window titles
        "brandLogoAlt": "Apache Superset powered by coasti",  # Logo alt text
        "brandLogoUrl": "/static/assets/custom/images/coasti_logo.png",
        "brandLogoHref": LOGO_TARGET_PATH or "/",
    },
}

FAVICONS = [{"href": "/static/assets/custom/images/coasti_favicon.png"}]

# IBCS color schemes to be added in dashboard settings
EXTRA_CATEGORICAL_COLOR_SCHEMES = [
    {
        "id": 'olympicColors',
        "description": '',
        "label": 'Colors of the Olympic Rings',
        "isDefault": False,
        "colors":
         ['#4594CC', '#FAD749', '#353535', '#43964A', '#BB3D37']
    },
    {
        "id": 'xylophoneColors',
        "description": '',
        "label": 'Colors of a typical toy Xylophone',
        "isDefault": False,
        "colors":
         ['#FF0000', '#FFA500', '#FFFF00', '#008000', '#0000FF', '#000080', '#663399', '#FFC0CB']
    },
    {
        "id": 'IBCS_Colors',
        "description": 'IBCS rules',
        "label": 'IBCS Grau',
        "isDefault": False,
        "colors":
         ['#595959', '#000000']
    },
    {
        "id": 'IBCS_Colors_2',
        "description": 'IBCS rules',
        "label": 'IBCS Grau',
        "isDefault": False,
        "colors":
         ['#000000', '#595959']
    },
    {
       "id": 'IBCS_Colors_3',
       "description": 'IBCS rules',
       "label": 'IBCS Grau',
       "isDefault": False,
       "colors":
        ['#3f3f3f','#595959', '#808080','#bfbfbf','#d8d8d8']
    }
]
# ------------------------ End Customizations ------------------------ #
