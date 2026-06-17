import logging
import pprint
import sys
from typing import Dict, Optional

from flask import g, redirect, request
from flask_appbuilder import expose
from superset import security_manager
from superset.initialization import SupersetIndexView as CoreSupersetIndexView
try:
    from superset.typing import FlaskResponse
except ModuleNotFoundError:  # pragma: no cover - legacy import path
    from superset.superset_typing import FlaskResponse  # type: ignore
from superset.utils.core import get_user_id

ROLE_REDIRECT_RULES: Dict[str, str] = {}
DEFAULT_REDIRECT_PATH = "/dashboard/list"

def _load_role_based_redirections_from_keycloak_yaml() -> Dict[str, str]:
    """Attempt to read `role_based_redirections` from the Keycloak YAML config.

    Re-uses the YAML loading logic from `KeycloakSecurityManager` by importing
    the module (it already resolves config paths and env var
    `KEYCLOAK_CONFIG_FILE`). Returns an empty dict on any error.
    """
    try:
        import KeycloakSecurityManager as ksm  # module is on pythonpath in this repo

        raw = getattr(ksm, "_yaml_settings", {}) or {}
        client = raw.get("client", raw)
        rb = client.get("role_based_redirections") or {}
        if isinstance(rb, dict):
            return {k: v for k, v in rb.items() if k and v}
    except Exception:
        # fail-safe: don't propagate import/load errors during app init
        pass
    return {}


# Initialize from YAML if present. Call this at module import so the rules are
# available before `set_role_redirect_rules` may be invoked by the config.
ROLE_REDIRECT_RULES = {}

def set_role_redirect_rules(default_path: Optional[str] = None) -> None:
    """Reload role-based redirect rules from Keycloak YAML and set default.

    This function no longer accepts an explicit `rules` dict — redirects are
    always read dynamically from `keycloak_clients.yml`. The optional
    `default_path` sets the fallback target when no role matches.
    """
    global ROLE_REDIRECT_RULES, DEFAULT_REDIRECT_PATH
    ROLE_REDIRECT_RULES = _load_role_based_redirections_from_keycloak_yaml() or {}
    if default_path:
        DEFAULT_REDIRECT_PATH = default_path

def _role_based_redirect(source: str) -> FlaskResponse:
    logging.debug(
        "Role redirect: invoked from %s for path=%s", source, request.path
    )

    if not g.user or not get_user_id():
        logging.warning("Role redirect: anonymous user detected; redirect to /login")
        return redirect("/login")

    try:
        from superset.extensions import appbuilder as current_appbuilder

        security_mgr = getattr(current_appbuilder, "sm", security_manager)
    except Exception:  # pragma: no cover - fallback for initialization edge cases
        security_mgr = security_manager

    user_roles = security_mgr.get_user_roles()
    username = getattr(getattr(g, "user", None), "username", "unknown")

    logging.warning(
        "Role redirect: evaluating username=%s with security manager %s; roles=%s",
        username,
        security_mgr.__class__.__name__,
        pprint.pformat(user_roles),
    )

    for role in user_roles:
        role_name = role.name
        logging.warning("Role redirect: inspecting role %s -- %s", role_name, role)

        target_path = ROLE_REDIRECT_RULES.get(role_name)
        if target_path:
            logging.warning(
                "Role redirect: role %s matched; redirecting username=%s to %s",
                role_name,
                username,
                target_path,
            )
            return redirect(target_path)

    logging.warning(
        "Role redirect: no specific role matched for username=%s; redirecting to /dashboard/list",
        username,
    )
    fallback_target = DEFAULT_REDIRECT_PATH or "/dashboard/list"
    return redirect(fallback_target)


class RoleRedirectIndexView(CoreSupersetIndexView):
    @expose("/")
    def index(self):
        logging.warning(
            "Role redirect: RoleRedirectIndexView triggered via %s",
            self.__class__.__name__,
        )
        return _role_based_redirect(self.__class__.__name__)


def mutate_app(app):
    from superset.views.core import Superset as CoreSupersetView

    if not getattr(CoreSupersetView, "_role_redirect_welcome_installed", False):
        original_welcome = getattr(CoreSupersetView, "welcome", None)

        def _role_redirect_welcome(self, *args, **kwargs):
            logging.debug(
                "Role redirect: Superset.welcome override via %s",
                self.__class__.__name__,
            )
            return _role_based_redirect("Superset.welcome")

        CoreSupersetView.welcome = _role_redirect_welcome
        setattr(CoreSupersetView, "_role_redirect_welcome_installed", True)
        setattr(CoreSupersetView, "_role_redirect_original_welcome", original_welcome)
        logging.debug("Role redirect: patched Superset.welcome at class level")

    return app


_CURRENT_MODULE = sys.modules[__name__]

try:
    import superset as superset_pkg  # type: ignore

    sys.modules.setdefault("RoleBasedRedirector", _CURRENT_MODULE)
    sys.modules["superset.RoleBasedRedirector"] = _CURRENT_MODULE
    setattr(superset_pkg, "RoleBasedRedirector", _CURRENT_MODULE)
    FAB_INDEX_VIEW_PATH = "superset.RoleBasedRedirector.RoleRedirectIndexView"
except ModuleNotFoundError:  # pragma: no cover - fallback for unit tests
    FAB_INDEX_VIEW_PATH = "RoleBasedRedirector.RoleRedirectIndexView"

FLASK_APP_MUTATOR = mutate_app
