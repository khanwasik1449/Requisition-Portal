from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter(is_safe=True)
def indian_number(value):
    try:
        value = int(float(value))
    except (ValueError, TypeError):
        return value

    if value < 0:
        return '-' + _format_indian(-value)

    return _format_indian(value)


def _format_indian(n):
    s = str(n)
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while len(rest) > 0:
        groups.append(rest[-2:] if len(rest) >= 2 else rest)
        rest = rest[:-2]
    groups.reverse()
    groups.append(last3)
    return ','.join(groups)
