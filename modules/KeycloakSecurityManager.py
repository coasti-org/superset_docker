import logging
import os
from pathlib import Path

import jwt
import yaml
from flask import g

logger = logging.getLogger(__name__)


def _load_keycloak_settings() -> dict:
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

    data = {}
    for config_path in candidates:
        if config_path.is_file():
            logger.debug("Loading Keycloak YAML settings from %s", config_path)
            with config_path.open(encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            break
    else:
        logger.debug("Keycloak YAML settings not found in candidates %s; using defaults", candidates)
    # Accept either top-level keys or a nested "client" mapping
    client_data = data.get("client", data)
    logger.debug("Keycloak YAML settings resolved to: %s", client_data)
    return client_data


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


def _build_auth_roles_mapping():
    """Build a mapping of Superset role -> list of Keycloak roles from YAML.

    The YAML file may define `auth_role_mappings` as KeycloakRole: SupersetRole
    or KeycloakRole: [SupersetRoleA, SupersetRoleB]. This function inverts
    that mapping into the shape expected by Superset: {sup_role: [kc_roles...]}
    """
    raw = _yaml_settings.get("auth_role_mappings") or {}
    mapping = {}
    for kc_role, sup_value in raw.items():
        if isinstance(sup_value, (list, tuple)):
            sup_roles = sup_value
        else:
            sup_roles = [sup_value]
        for sup in sup_roles:
            if not sup:
                continue
            mapping.setdefault(sup, []).append(kc_role)
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
        logger.debug("User info from Keycloak: %s", data)
        logger.debug("User info realm roles: %s", data.get("realm_access", {}).get("roles", []))

        access_token = response.get("access_token")
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        roles = decoded_token.get("realm_access", {}).get("roles", [])
        logger.debug("Realm roles extracted from JWT: %s", roles)

        # Map Keycloak realm roles to Superset role keys using AUTH_ROLES_MAPPING.
        mapped = set()
        for sup_role, kc_roles in AUTH_ROLES_MAPPING.items():
            if any(r in roles for r in kc_roles):
                mapped.add(sup_role)

        role_keys = list(mapped) if mapped else roles

        return {
            "username": data.get("preferred_username", ""),
            "first_name": data.get("given_name", ""),
            "last_name": data.get("family_name", ""),
            "email": data.get("email", ""),
            "role_keys": role_keys,
        }

    def load_user_jwt(self, _jwt_header, jwt_data):
        username = jwt_data["preferred_username"]
        user = self.find_user(username=username)
        if user:
            logger.debug("Hydrated user %s (%s) via JWT", username, user.id)
        else:
            logger.debug("JWT user %s not found in Superset", username)
        if user.is_active:
            g.user = user
            logger.debug("JWT user %s marked active and stored on flask.g", username)
            return user
        logger.debug("JWT user %s inactive; rejecting login", username)
        return None


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
