"""Seed the portal with configuration for the built-in modules.

Transport gets the full chain the business asked for:

    supervisor -> grants -> transport admin (assign vehicle + driver)

Grants may amend the project and budget code before approving. ICT and Internal
are seeded with the two-stage chain they already use, so switching a module onto
the engine later is a matter of pointing its views at ``portal_config`` rather
than re-entering its configuration.

Existing requisitions are left alone: rows that sit on the old
``pending_second`` status are migrated to the equivalent new stage.
"""

from django.db import migrations

TRANSPORT_FIELDS = [
    # (step, order, key, label, type, required, help_text, placeholder)
    (1, 1, 'full_name', 'Full name', 'text', True, '', 'e.g. Rafiqul Islam'),
    (1, 2, 'email_address', 'Email address', 'email', True, 'Use your BRAC University email.', 'you@bracu.ac.bd'),
    (1, 3, 'mobile_number', 'Mobile number', 'tel', True, 'Active number for the day of travel.', '01XXXXXXXXX'),
    (1, 4, 'designation', 'Designation', 'text', True, '', 'e.g. Senior Programme Officer'),
    (1, 5, 'pin', 'PIN', 'text', True, 'Your BRAC University employee ID.', 'e.g. 10432'),
    (1, 6, 'num_passengers', 'Number of passengers', 'number', True, 'Including yourself.', '3'),

    (2, 1, 'vehicle_type', 'Vehicle required', 'select', True, 'Pick the smallest vehicle that fits.', ''),
    (2, 2, 'vehicle_type_other', 'Or specify', 'text', False, 'Required when you choose Other.', 'e.g. Pick-up'),
    (2, 3, 'pick_up_date', 'Pick-up date', 'date', True, '', ''),
    (2, 4, 'pick_up_time', 'Pick-up time', 'time', True, '', ''),
    (2, 5, 'pick_up_location', 'Pick-up location', 'text', True, '', 'e.g. BRAC University, Meruland'),
    (2, 6, 'destination', 'Destination', 'text', True, '', 'e.g. Savar, Dhaka'),
    (2, 7, 'drop_off_date', 'Drop-off date', 'date', True, '', ''),
    (2, 8, 'drop_off_time', 'Drop-off time', 'time', True, '', ''),
    (2, 9, 'drop_off_location', 'Drop-off location', 'text', True, '', 'e.g. BRAC University, Meruland'),

    (3, 1, 'travelling_reason', 'Reason for travelling', 'textarea', True, 'Be specific — it helps approvals go through faster.', ''),
    (3, 2, 'project_name_code', 'Project name and code', 'text', True, 'The Grants team checks this against their records.', 'e.g. Academic- M.ED (0002)'),

    (4, 1, 'budget_code', 'Budget code', 'text', True, 'Must belong to the project selected above. Grants can correct this.', 'e.g. 0002-401010106'),

    (5, 1, 'supervisor_acknowledged', 'Supervisor acknowledgement', 'checkbox', True, '', ''),
    (5, 2, 'comments_remarks', 'Comments or remarks', 'textarea', False, 'Anything the approver should know.', ''),
]

VEHICLE_TYPE_OPTIONS = '\n'.join([
    'sedan|Sedan Car (3 Users)',
    'noah|Micro Noah (7 Users)',
    'hiace_11|Micro Hi-Ace (11 Users)',
    'hiace_14|Micro Hi-Ace (14 Users)',
    'delivery_van|Delivery Van (Covered Van, Pickup etc.)',
    'other|Other',
])

TRANSPORT_STAGES = [
    # (order, key, name, role, actions, terminal)
    (1, 'pending_first', 'Supervisor Approval', 'supervisor', 'approve,decline', False),
    (2, 'pending_grants', 'Grants Approval', 'grants', 'approve,decline,amend', False),
    (3, 'pending_transport', 'Transport Admin — Vehicle & Driver', 'transport_admin', 'approve,decline,assign', False),
    (4, 'assigned', 'Vehicle and Driver Assigned', 'transport_admin', 'approve', True),
]

# Grants may correct the funding codes before passing the request on.
GRANTS_AMENDABLE = ['project_name_code', 'budget_code']


def seed(apps, schema_editor):
    Module = apps.get_model('portal_config', 'Module')
    FormField = apps.get_model('portal_config', 'FormField')
    WorkflowStage = apps.get_model('portal_config', 'WorkflowStage')
    TransportRequisition = apps.get_model('transport_requisition', 'TransportRequisition')

    transport, _ = Module.objects.update_or_create(
        key='transport',
        defaults={
            'name': 'Transport Requisition',
            'description': 'Vehicle requisition for official travel.',
            'is_active': True,
            'order': 1,
        },
    )

    for step, order, key, label, ftype, required, help_text, placeholder in TRANSPORT_FIELDS:
        options = VEHICLE_TYPE_OPTIONS if key == 'vehicle_type' else ''
        FormField.objects.update_or_create(
            module=transport,
            key=key,
            defaults={
                'label': label,
                'field_type': ftype,
                'help_text': help_text,
                'placeholder': placeholder,
                'step': step,
                'order': order,
                'required': required,
                # Every seeded field maps to a real column, so reports and the
                # Excel export keep working.
                'is_system': True,
                'visible_to_requester': True,
                'show_in_review': True,
                'options': options,
                'config': {'min': 1, 'max': 50} if key == 'num_passengers' else {},
            },
        )

    fields_by_key = {f.key: f for f in FormField.objects.filter(module=transport)}

    for order, key, name, role, actions, terminal in TRANSPORT_STAGES:
        stage, _ = WorkflowStage.objects.update_or_create(
            module=transport,
            key=key,
            defaults={
                'name': name,
                'order': order,
                'approver_role': role,
                'actions': actions,
                'require_reason_on_decline': True,
                'is_terminal': terminal,
                'is_active': True,
            },
        )
        # Only the Grants stage may correct the funding codes; everyone else
        # gets an empty set.
        if key == 'pending_grants':
            stage.amendable_fields.set(
                [fields_by_key[k] for k in GRANTS_AMENDABLE if k in fields_by_key]
            )
        else:
            stage.amendable_fields.clear()

    # Re-point requisitions created before this migration. 'pending_second' was
    # the old single second-stage status; it is now the Grants stage. Anything
    # already fully approved stays approved.
    TransportRequisition.objects.filter(status='pending_second').update(status='pending_grants')

    # ICT and Internal keep their existing two-stage chain. Seeded so the portal
    # can show and edit them, not yet wired into their views.
    for order, (key, name) in enumerate(
        [('ict', 'ICT Requisition'), ('internal', 'Internal Requisition')], start=2
    ):
        module, _ = Module.objects.update_or_create(
            key=key,
            defaults={'name': name, 'is_active': True, 'order': order},
        )
        WorkflowStage.objects.update_or_create(
            module=module, key='pending_first',
            defaults={'name': 'First Approval', 'order': 1, 'approver_role': 'supervisor',
                      'actions': 'approve,decline', 'is_terminal': False, 'is_active': True},
        )
        WorkflowStage.objects.update_or_create(
            module=module, key='pending_second',
            defaults={'name': 'Second Approval', 'order': 2, 'approver_role': 'ict_approver',
                      'actions': 'approve,decline', 'is_terminal': False, 'is_active': True},
        )
        WorkflowStage.objects.update_or_create(
            module=module, key='approved',
            defaults={'name': 'Approved', 'order': 3, 'approver_role': '',
                      'actions': 'approve', 'is_terminal': True, 'is_active': True},
        )


def unseed(apps, schema_editor):
    Module = apps.get_model('portal_config', 'Module')
    Module.objects.filter(key__in=['transport', 'ict', 'internal']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('portal_config', '0001_initial'),
        ('accounts', '0005_alter_user_role'),
        ('transport_requisition', '0006_vehicle_transportrequisition_extra_data_and_more'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]