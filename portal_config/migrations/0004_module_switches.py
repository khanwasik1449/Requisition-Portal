"""Add the on/off switches to Module and seed them from settings.

The flags used to live only in ``settings.ENABLED_MODULES`` and
``settings.VISIBLE_MODULES``. They are now editable from the superuser Form
Builder screen, so each Module row carries its own copy. This migration creates
the columns and backfills them from the settings lists, so a deploy that has
never touched the UI behaves exactly as settings.py declared.
"""

from django.conf import settings
from django.db import migrations, models


def seed_flags(apps, schema_editor):
    Module = apps.get_model('portal_config', 'Module')

    enabled = set(getattr(settings, 'ENABLED_MODULES', []))
    visible = set(getattr(settings, 'VISIBLE_MODULES', []))

    for module in Module.objects.all():
        module.is_enabled = module.key in enabled
        module.is_visible = module.key in visible
        module.save(update_fields=['is_enabled', 'is_visible'])


def unseed_flags(apps, schema_editor):
    Module = apps.get_model('portal_config', 'Module')
    Module.objects.update(is_enabled=True, is_visible=True)


class Migration(migrations.Migration):

    dependencies = [
        ('portal_config', '0003_alter_workflowstage_approver_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='module',
            name='is_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='module',
            name='is_visible',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(seed_flags, unseed_flags),
    ]
