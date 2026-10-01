"""URL routing that follows the module on/off switches.

The root URL conf is imported once per worker process, so building
``urlpatterns`` from the database at import time would freeze the routing until
every worker is restarted. Instead each module's URLs are wrapped in a resolver
that checks the module's ``is_enabled`` flag on every request, so switching a
module off in the Form Builder 404s it immediately and switching it back on
makes it routable again -- no restart.
"""

from django.urls import Resolver404, include
from django.urls.resolvers import RoutePattern, URLResolver

from portal_config.engine import enabled_module_keys


class ModuleURLResolver(URLResolver):
    """Resolves a module's URLs only while that module is enabled.

    The enabled check is a single indexed lookup over a handful of
    ``portal_config.Module`` rows, so it is cheap enough to run on every
    request. The result is deliberately not cached on the instance: caching it
    here would reintroduce the staleness this class exists to avoid.
    """

    def __init__(self, module_key, route, urlconf_name, app_name=None, namespace=None):
        self.module_key = module_key
        super().__init__(
            RoutePattern(route, is_endpoint=False),
            urlconf_name,
            app_name=app_name,
            namespace=namespace,
        )

    def resolve(self, path):
        if self.module_key not in enabled_module_keys():
            raise Resolver404({'path': path})
        return super().resolve(path)


def module_include(module_key, route, urlconf_name):
    """``include()`` that honours the module's on/off switch.

    ``include()`` returns a ``(urlconf_module, app_name, namespace)`` tuple that
    Django turns into a URLResolver. Building the resolver directly means
    reproducing that tuple's namespace handling here, so named URLs inside the
    module still reverse correctly while the module is enabled.

    The namespace defaults to the urlconf's ``app_name``, exactly as ``include()``
    does. Getting this wrong makes every ``{% url 'module:name' %}`` in the
    project resolve to the wrong module, because Django keys namespaced lookups
    by namespace and a ``None`` namespace collides across modules.
    """
    if isinstance(urlconf_name, str):
        urlconf_module = __import__(urlconf_name, fromlist=['urlpatterns'])
    else:
        urlconf_module = urlconf_name

    app_name = getattr(urlconf_module, 'app_name', None)
    return ModuleURLResolver(
        module_key, route, urlconf_module,
        app_name=app_name, namespace=app_name,
    )
