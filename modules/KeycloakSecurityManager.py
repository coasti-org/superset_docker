import logging
import os
from pathlib import Path

import jwt
import yaml
from flask import current_app, g

logger = logging.getLogger(__name__)


def _keycloak_config_candidates():
    env_path = os.environ.get("KEYCLOAK_CONFIG_FILE")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))
    # Common locations inside the container for this repo layout
    candidates.extend(
        [
            Path("/app/superset/auth_keycloak/keycloak_clients.yml"),
        ]
    )
    return candidates


# Cache of the last-loaded YAML settings, keyed by (path, mtime) so that
# per-request callers (oauth_user_info, role-based redirects) can pick up
# edits to keycloak_clients.yml without requiring a container restart.
# Note: connection-level settings (host/realm/client_id/client_secret) are
# still only read once below, since they configure the OAuth client at
# app startup and can't be swapped live without re-registering it.
_yaml_cache = {"path": None, "mtime": None, "data": {}}


def _load_keycloak_settings() -> dict:
    candidates = _keycloak_config_candidates()
    for config_path in candidates:
        if config_path.is_file():
            mtime = config_path.stat().st_mtime
            if _yaml_cache["path"] == config_path and _yaml_cache["mtime"] == mtime:
                return _yaml_cache["data"]
            logger.debug("Loading Keycloak YAML settings from %s", config_path)
            with config_path.open(encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            client_data = data.get("client", data)
            _yaml_cache.update(path=config_path, mtime=mtime, data=client_data)
            logger.debug("Keycloak YAML settings resolved to: %s", client_data)
            return client_data
    logger.debug("Keycloak YAML settings not found in candidates %s; using defaults", candidates)
    return {}


_yaml_settings = _load_keycloak_settings()


def _get_setting(env_key: str, yaml_key: str, default: str) -> str:
    value = os.environ.get(env_key) or _yaml_settings.get(yaml_key, default)
    logger.debug(
        "Keycloak config: %s/%s resolved to %s", env_key, yaml_key, value
    )
    return value


KEYCLOAK_EXTERNAL_HOST = _get_setting(
    "KEYCLOAK_EXTERNAL_HOST", "host", "https://keycloak.example.com"
)
KEYCLOAK_REALM = _get_setting("KEYCLOAK_REALM", "realm", "")
KEYCLOAK_CLIENT_ID = _get_setting("KEYCLOAK_CLIENT_ID", "client_id", "")
KEYCLOAK_CLIENT_SECRET = _get_setting(
    "KEYCLOAK_CLIENT_SECRET", "client_secret", ""
)

_host = KEYCLOAK_EXTERNAL_HOST.rstrip("/")
KEYCLOAK_BASE_URL = f"{_host}/realms/{KEYCLOAK_REALM}"

LOGOUT_REDIRECT_URL = f"{KEYCLOAK_BASE_URL}/protocol/openid-connect/logout"
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_BASE_URL}/protocol/openid-connect/token"
KEYCLOAK_USERINFO_URL = f"{KEYCLOAK_BASE_URL}/protocol/openid-connect/userinfo"
KEYCLOAK_JWKS_URL = f"{KEYCLOAK_BASE_URL}/protocol/openid-connect/certs"

OAUTH_PROVIDERS = [
    {
        "name": "keycloak",
        "icon": "fa-key",
        "token_key": "access_token",
        "remote_app": {
            "client_id": f"{KEYCLOAK_CLIENT_ID}",
            "client_secret": f"{KEYCLOAK_CLIENT_SECRET}",
            "client_kwargs": {
                "scope": "openid profile email",
            },
            "server_metadata_url": f"{KEYCLOAK_BASE_URL}/.well-known/openid-configuration",
            "api_base_url": f"{KEYCLOAK_BASE_URL}/protocol/",
            "access_token_url": KEYCLOAK_TOKEN_URL,
            "authorize_url": f"{KEYCLOAK_BASE_URL}/protocol/openid-connect/auth",
        },
    }
]


def _build_auth_roles_mapping(settings: dict | None = None):
    """Build the Keycloak role -> Superset role(s) mapping from YAML.

    The YAML file defines `auth_role_mappings` as KeycloakRole: SupersetRole
    or KeycloakRole: [SupersetRoleA, SupersetRoleB]. This is returned as-is
    in the shape {kc_role: [sup_roles...]}, which is exactly what
    Flask-AppBuilder's AUTH_ROLES_MAPPING / get_roles_from_keys expects
    (key = external/provider role key, value = local Superset role names).

    :param settings: pre-loaded YAML settings dict; defaults to a fresh
        `_load_keycloak_settings()` call so callers get up-to-date mappings
        even if `keycloak_clients.yml` changed after the app started.
    """
    if settings is None:
        settings = _load_keycloak_settings()
    raw = settings.get("auth_role_mappings") or {}
    mapping = {}
    for kc_role, sup_value in raw.items():
        if not kc_role:
            continue
        if isinstance(sup_value, (list, tuple)):
            sup_roles = [sup for sup in sup_value if sup]
        else:
            sup_roles = [sup_value] if sup_value else []
        if sup_roles:
            mapping[kc_role] = sup_roles
    logger.debug("AUTH_ROLES_MAPPING resolved to: %s", mapping)
    return mapping


AUTH_ROLES_MAPPING = _build_auth_roles_mapping()

from superset.security import SupersetSecurityManager


class KeycloakSecurityManager(SupersetSecurityManager):
    def oauth_user_info(self, provider, response=None):  # noqa: ARG002
        logger.debug("Fetching OAuth user info for provider=%s", provider)
        me = self.appbuilder.sm.oauth_remotes[provider].get("openid-connect/userinfo")
        me.raise_for_status()
        data = me.json()
        username = data.get("preferred_username", "")
        logger.debug("[user=%s] User info from Keycloak: %s", username, data)

        access_token = response.get("access_token")
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        roles = decoded_token.get("realm_access", {}).get("roles", [])
        logger.debug("[user=%s] Realm roles extracted from JWT: %s", username, roles)

        # Refresh AUTH_ROLES_MAPPING from keycloak_clients.yml on every login,
        # so role mapping edits take effect immediately without a container
        # restart. Flask-AppBuilder reads current_app.config["AUTH_ROLES_MAPPING"]
        # fresh on each request (see auth_roles_mapping property), so updating
        # it here is picked up by the role-sync step that runs right after
        # oauth_user_info returns.
        current_app.config["AUTH_ROLES_MAPPING"] = _build_auth_roles_mapping()

        # Return the raw Keycloak realm roles as role_keys. Flask-AppBuilder's
        # own OAuth role-sync (AUTH_ROLES_SYNC_AT_LOGIN / AUTH_ROLES_MAPPING,
        # wired in superset_config.py from AUTH_ROLES_MAPPING below) uses these
        # role_keys together with AUTH_ROLES_MAPPING to resolve the actual
        # Superset roles. Pre-mapping here would double-map and break lookup.
        role_keys = roles

        return {
            "username": username,
            "first_name": data.get("given_name", ""),
            "last_name": data.get("family_name", ""),
            "email": data.get("email", ""),
            "role_keys": role_keys,
        }

    def load_user_jwt(self, _jwt_header, jwt_data):
        username = jwt_data["preferred_username"]
        user = self.find_user(username=username)
        if user is None:
            logger.debug("[user=%s] JWT user not found in Superset", username)
            return None
        if not user.is_active:
            logger.debug("[user=%s] JWT user inactive; rejecting login", username)
            return None
        g.user = user
        logger.debug("[user=%s] Hydrated user (id=%s) via JWT and marked active", username, user.id)
        return user


def configure_keycloak_oauth(appbuilder):
    keycloak_remote = appbuilder.sm.oauth_remotes.get("keycloak")
    if not keycloak_remote:
        logger.debug("Keycloak remote not registered; skipping OAuth configuration patch")
        return

    original_loader = getattr(keycloak_remote, "load_server_metadata", None)

    def _patch_metadata(metadata):
        logger.debug("Patching Keycloak metadata endpoints")
        metadata["token_endpoint"] = KEYCLOAK_TOKEN_URL
        metadata["userinfo_endpoint"] = KEYCLOAK_USERINFO_URL
        metadata["jwks_uri"] = KEYCLOAK_JWKS_URL
        return metadata

    if original_loader:
        logger.debug("Wrapping Keycloak remote load_server_metadata for endpoint overrides")
        def patched_loader(*args, **kwargs):
            metadata = original_loader(*args, **kwargs)
            return _patch_metadata(metadata)

        keycloak_remote.load_server_metadata = patched_loader

    server_metadata = getattr(keycloak_remote, "server_metadata", None)
    if server_metadata:
        logger.debug("Applying metadata patch to cached Keycloak server metadata")
        _patch_metadata(server_metadata)


CUSTOM_SECURITY_MANAGER = KeycloakSecurityManager

__all__ = [
    "LOGOUT_REDIRECT_URL",
    "OAUTH_PROVIDERS",
    "CUSTOM_SECURITY_MANAGER",
    "configure_keycloak_oauth",
]
