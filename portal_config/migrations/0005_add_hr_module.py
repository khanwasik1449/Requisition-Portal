"""Add the HR module row so it can be switched on and off like the others.

HR is three apps (contracts, employees, payslip) rather than one, so it was
routed as a group and had no Module row of its own. Giving it one lets the
superadmin toggle it from the same screen as every other module.
"""

from django.conf import settings
from django.db import migrations


def add_hr(apps, schema_editor):
    Module = apps.get_model('portal_config', 'Module')
    enabled = set(getattr(settings, 'ENABLED_MODULES', []))
    visible = set(getattr(settings, 'VISIBLE_MODULES', []))

    Module.objects.update_or_create(
        key='hr',
        defaults={
            'name': 'Human Resources',
            'description': 'Contracts, employees and payslips.',
            'is_active': True,
            'order': 4,
            'is_enabled': 'hr' in enabled,
            'is_visible': 'hr' in visible,
        },
    )


def remove_hr(apps, schema_editor):
    Module = apps.get_model('portal_config', 'Module')
    Module.objects.filter(key='hr').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('portal_config', '0004_module_switches'),
    ]

    operations = [
        migrations.RunPython(add_hr, remove_hr),
    ]
