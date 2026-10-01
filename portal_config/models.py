"""Database-driven configuration for requisition forms and workflows.

Everything here is keyed by ``Module.key`` (the same keys used in
``settings.ENABLED_MODULES`` -- 'transport', 'ict', 'internal', ...). A module is
described entirely by rows in this app, so a new requisition type can be added
later without touching workflow code.

Two things are configurable:

``FormField``
    The fields that make up a module's public request form: label, widget type,
    whether it is required, which step it sits on, and whether it is stored in a
    real model column or in the requisition's ``extra_data`` JSON blob.

``WorkflowStage``
    An ordered approval stage. Each stage names the role allowed to act on it
    and declares what that role may do (approve / decline / amend specific
    fields / assign a vehicle and driver). A requisition's status is simply the
    key of the stage it is currently sitting in.
"""

from django.conf import settings
from django.db import models
from django.utils.functional import lazy


def _user_role_choices():
    """Resolve the role choices at import time, without a circular import.

    ``accounts.models`` does not depend on this app, but importing it lazily
    keeps the dependency one-directional even if that changes later.

    Passed to the field as a callable rather than a materialised list: Django
    then leaves it out of migrations entirely, so adding a role to
    ``accounts.User.Role`` needs no migration here.
    """
    from accounts.models import User
    return User.Role.choices


class Module(models.Model):
    """A configurable requisition type.

    ``key`` matches ``settings.ENABLED_MODULES``. The model/table each module
    writes to is resolved at runtime by ``portal_config.registry``.
    """

    key = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    # On/off switches, editable from the superuser Form Builder screen.
    #
    # `is_enabled` is the hard switch: a disabled module is not routed, so its
    # URLs 404 and its data is unreachable. `is_visible` is the soft switch: the
    # module stays routed and its data intact, but disappears from the nav,
    # dashboard and "My Requisitions".
    #
    # Both fall back to settings.ENABLED_MODULES / VISIBLE_MODULES when the
    # database cannot be read, so routing never breaks during migrations or on
    # a fresh deploy before the config tables exist.
    is_enabled = models.BooleanField(default=True)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name or self.key


class FieldType(models.TextChoices):
    TEXT = 'text', 'Text'
    TEXTAREA = 'textarea', 'Long text'
    EMAIL = 'email', 'Email'
    TEL = 'tel', 'Phone'
    NUMBER = 'number', 'Number'
    DATE = 'date', 'Date'
    TIME = 'time', 'Time'
    DATETIME = 'datetime', 'Date and time'
    SELECT = 'select', 'Dropdown'
    CHECKBOX = 'checkbox', 'Checkbox'
    RADIO = 'radio', 'Radio buttons'


class FormField(models.Model):
    """One field on a module's public request form.

    ``key`` is the stable machine name. When ``is_system`` is true the value is
    stored in the identically-named column on the module's requisition model, so
    reports, exports and filtering keep working. When it is false the value is
    written to the requisition's ``extra_data`` JSONField instead -- that is how
    an admin adds a brand new field without a migration.
    """

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='fields')
    key = models.SlugField(max_length=60)
    label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=FieldType.choices, default=FieldType.TEXT)
    help_text = models.TextField(blank=True)
    placeholder = models.CharField(max_length=200, blank=True)

    step = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)

    required = models.BooleanField(default=False)
    is_system = models.BooleanField(
        default=True,
        help_text='Stored in a real database column. Uncheck for fields added by an '
                  'administrator, whose values are kept in the extra_data JSON blob.',
    )
    visible_to_requester = models.BooleanField(default=True)
    show_in_review = models.BooleanField(default=True)

    # Populated for SELECT / RADIO. One option per entry.
    options = models.TextField(
        blank=True,
        help_text='One choice per line, as "value|Label shown to the user".',
    )

    # Extra widget hints, e.g. {"max": 30} or {"rows": 4}.
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['module', 'step', 'order', 'id']
        constraints = [
            models.UniqueConstraint(fields=['module', 'key'], name='unique_field_key_per_module'),
        ]

    def __str__(self):
        return f'{self.module.key}.{self.key}'

    @property
    def option_list(self):
        """Parse ``options`` into ``[(value, label), ...]``."""
        parsed = []
        for line in (self.options or '').splitlines():
            line = line.strip()
            if not line:
                continue
            value, _, label = line.partition('|')
            parsed.append((value.strip(), (label or value).strip()))
        return parsed

    @property
    def input_type(self):
        """The HTML input type that matches this field.

        ``datetime`` is a choice label, not a real input type, so it maps to
        ``datetime-local``. Everything else is already a valid input type.
        """
        return 'datetime-local' if self.field_type == 'datetime' else self.field_type


class StageAction(models.TextChoices):
    APPROVE = 'approve', 'Approve'
    DECLINE = 'decline', 'Decline'
    AMEND = 'amend', 'Amend fields then approve'
    ASSIGN = 'assign', 'Assign vehicle and driver'


class WorkflowStage(models.Model):
    """One step in a module's approval chain.

    ``key`` doubles as the requisition's status while it sits at this stage, so
    renaming a stage's label never invalidates existing rows. Stages are chained
    by ``order``; ``is_terminal`` marks the ones that end the workflow.
    """

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='stages')
    key = models.SlugField(max_length=40)
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    # Which role may act at this stage. Empty means "no restriction beyond
    # is_approver()", which keeps single-approver setups simple.
    approver_role = models.CharField(
        max_length=20, blank=True, choices=_user_role_choices,
        help_text='Only users holding this role can act at this stage. '
                  'Leave blank to allow any approver.',
    )
    # `choices` is a callable, so Django treats the field as unchanged whenever
    # the callable's identity is the same -- no migration per new role.

    actions = models.CharField(
        max_length=100,
        default='approve,decline',
        help_text='Comma-separated: approve, decline, amend, assign.',
    )
    require_reason_on_decline = models.BooleanField(default=True)

    # When 'amend' is an allowed action, these are the fields this stage may
    # change. The Grants stage, for example, amends project and budget code.
    amendable_fields = models.ManyToManyField(
        FormField, blank=True, related_name='amendable_at_stages',
        help_text='Fields this stage is allowed to change before approving.',
    )

    is_terminal = models.BooleanField(
        default=False,
        help_text='Tick for the final stage (approved / rejected / fulfilled).',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['module', 'order', 'id']
        constraints = [
            models.UniqueConstraint(fields=['module', 'key'], name='unique_stage_key_per_module'),
        ]

    def __str__(self):
        return f'{self.module.key}: {self.name}'

    # -- capability helpers -------------------------------------------------
    @property
    def action_set(self):
        return {a.strip() for a in (self.actions or '').split(',') if a.strip()}

    def can(self, action):
        return action in self.action_set

    @property
    def can_approve(self):
        return self.can(StageAction.APPROVE)

    @property
    def can_decline(self):
        return self.can(StageAction.DECLINE)

    @property
    def can_amend(self):
        return self.can(StageAction.AMEND)

    @property
    def can_assign(self):
        return self.can(StageAction.ASSIGN)

    def amendment_target_keys(self):
        return [f.key for f in self.amendable_fields.all()]