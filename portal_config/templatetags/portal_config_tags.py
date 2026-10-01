"""Template helpers for rendering configuration-driven forms."""

from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Look up ``key`` in a dict, returning None when it is absent.

    Django templates silently resolve a missing dict key to the empty string,
    which makes ``{% if errors.pin %}`` false for both "no error" and "no such
    field". This keeps the two distinguishable.
    """
    if mapping is None:
        return None
    try:
        return mapping.get(key)
    except AttributeError:
        return None