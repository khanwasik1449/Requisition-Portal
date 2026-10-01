"""Seed MeetSpace into the workflow engine.

Gives the module a row in the Form Builder, a set of form fields for the
booking request, and a two-stage approval chain (HR admin approves or rejects).
"""

from django.conf import settings
from django.db import migrations

# (step, order, key, label, type, required, help_text, placeholder)
BOOKING_FIELDS = [
    (1, 1, 'meeting_title', 'Meeting title', 'text', True, '', 'e.g. Quarterly planning'),
    (1, 2, 'room', 'Room', 'select', True, 'Choose the room that fits your group.', ''),
    (1, 3, 'date', 'Date', 'date', True, '', ''),
    (1, 4, 'start_time', 'Start time', 'time', True, '', ''),
    (1, 5, 'end_time', 'End time', 'time', True, '', ''),
    (1, 6, 'number_of_participants', 'Participants', 'number', True, 'Including yourself.', ''),
    (1, 7, 'requirements', 'Requirements', 'textarea', False, 'Projector, video conferencing, whiteboard…', ''),
]

# (order, key, name, role, actions, terminal)
MEETSPACE_STAGES = [
    (1, 'pending', 'HR Admin Approval', 'hr_admin', 'approve,decline', False),
    (2, 'approved', 'Booked', '', 'approve', True),
]


def seed(apps, schema_editor):
    Module = apps.get_model('portal_config', 'Module')
    FormField = apps.get_model('portal_config', 'FormField')
    WorkflowStage = apps.get_model('portal_config', 'WorkflowStage')

    enabled = set(getattr(settings, 'ENABLED_MODULES', []))
    visible = set(getattr(settings, 'VISIBLE_MODULES', []))

    module, _ = Module.objects.update_or_create(
        key='meetspace',
        defaults={
            'name': 'MeetSpace',
            'description': 'Meeting room bookings.',
            'is_active': True,
            'order': 3,
            'is_enabled': 'meetspace' in enabled,
            'is_visible': 'meetspace' in visible,
        },
    )

    for step, order, key, label, ftype, required, help_text, placeholder in BOOKING_FIELDS:
        FormField.objects.update_or_create(
            module=module, key=key,
            defaults={
                'label': label, 'field_type': ftype, 'help_text': help_text,
                'placeholder': placeholder, 'step': step, 'order': order,
                'required': required, 'is_system': True,
                'visible_to_requester': True, 'show_in_review': True,
                'options': '', 'config': {},
            },
        )

    for order, key, name, role, actions, terminal in MEETSPACE_STAGES:
        WorkflowStage.objects.update_or_create(
            module=module, key=key,
            defaults={
                'name': name, 'order': order, 'approver_role': role,
                'actions': actions, 'require_reason_on_decline': True,
                'is_terminal': terminal, 'is_active': True,
            },
        )


def unseed(apps, schema_editor):
    Module = apps.get_model('portal_config', 'Module')
    Module.objects.filter(key='meetspace').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('meetspace', '0001_initial'),
        ('portal_config', '0005_add_hr_module'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
