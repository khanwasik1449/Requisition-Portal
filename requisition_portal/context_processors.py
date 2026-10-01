from django.conf import settings


def _can(user, method):
    """True if the user is an admin, or satisfies the named role predicate."""
    if user is None or not user.is_authenticated:
        return False
    if user.is_admin():
        return True
    return getattr(user, method)()


def portal(request):
    """Expose module feature flags to every template.

    ENABLED_MODULES decides what is routed; VISIBLE_MODULES decides what is
    shown. Templates gate on the visibility flags, so a hidden module's links
    are never reversed even though its URLs still resolve.

    Both are read from the database so the superuser can switch a module on or
    off from the Form Builder screen, falling back to settings when the config
    tables are unavailable.
    """
    from portal_config.engine import enabled_module_keys, visible_module_keys

    visible = visible_module_keys()
    enabled = enabled_module_keys()
    user = getattr(request, 'user', None)

    return {
        'enabled_modules': enabled,
        'visible_modules': visible,
        'hr_enabled': 'hr' in enabled,
        # Requisition modules: visible AND the user actually has that role.
        'can_ict': 'ict' in visible and _can(user, 'is_ict_admin'),
        'can_transport': 'transport' in visible and _can(user, 'is_transport_admin'),
        'can_internal': 'internal' in visible and _can(user, 'is_internal_admin'),
        'can_hr_admin': 'meetspace' in visible and _can(user, 'is_hr_admin'),
        # Off-site Google Forms, independent of module visibility.
        'external_forms': settings.EXTERNAL_FORMS,
    }
