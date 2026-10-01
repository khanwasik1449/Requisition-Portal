"""Runtime helpers for the dynamic form/workflow engine.

These functions are the only place the rest of the portal needs to know how to
turn ``portal_config`` rows into real behaviour: which module a request belongs
to, which fields its form has, how to validate a submission against those
fields, and where a requisition goes next when someone approves it.
"""

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .models import FormField, Module, StageAction, WorkflowStage

# Where each module's requisitions live. A module that is not listed here cannot
# be routed, even if it has configuration rows.
MODULE_MODELS = {
    'transport': ('transport_requisition', 'TransportRequisition'),
    'ict': ('ict_requisition', 'ICTRequisition'),
    'internal': ('internal_requisition', 'InternalRequisition'),
    'meetspace': ('meetspace', 'Booking'),
}


def _module_flag(flag_name, settings_fallback):
    """Read a boolean module flag from the database.

    Returns ``(keys, db_ok)``. ``db_ok`` is False when the config tables could
    not be read at all — during ``migrate``, or on a fresh deploy before the
    seed has run — in which case the settings list is the only source of truth
    and routing must fall back to it.

    When the database *can* be read its answer wins outright. A module whose
    row says "off" stays off even if settings.py still lists it, otherwise the
    switch in the Form Builder would do nothing. The only settings keys honoured
    without a Module row are those the seed has not created yet, so a fresh
    deploy still behaves as settings.py declares.
    """
    try:
        rows = list(Module.objects.values_list('key', flag_name))
    except Exception:
        return list(settings_fallback), False

    keys = [key for key, flag in rows if flag]
    known = {key for key, _ in rows}
    for key in settings_fallback:
        if key not in known:
            keys.append(key)
    return keys, True


def enabled_module_keys():
    """Module keys that are routed, read from the database.

    Falls back to ``settings.ENABLED_MODULES`` only when the config tables
    cannot be read, so routing never breaks during migrations or on a fresh
    deploy before the seed has run.
    """
    return _module_flag('is_enabled', settings.ENABLED_MODULES)[0]


def visible_module_keys():
    """Module keys shown in the UI, read from the database.

    Same fallback contract as :func:`enabled_module_keys`.
    """
    return _module_flag('is_visible', settings.VISIBLE_MODULES)[0]


def get_module(key):
    """Return the Module row for ``key``, or None."""
    return Module.objects.filter(key=key).first()


def get_model(module_key):
    """Return the requisition model backing a module."""
    target = MODULE_MODELS.get(module_key)
    if not target:
        return None
    try:
        return apps.get_model(*target)
    except LookupError:
        return None


def get_fields(module_key, only_visible=False):
    """Active form fields for a module, ordered the way the form renders them."""
    qs = FormField.objects.filter(module__key=module_key, module__is_active=True)
    if only_visible:
        qs = qs.filter(visible_to_requester=True)
    return list(qs.select_related('module'))


def get_stages(module_key):
    """Active workflow stages for a module, in chain order."""
    return list(
        WorkflowStage.objects.filter(module__key=module_key, module__is_active=True, is_active=True)
        .order_by('order', 'id')
    )


def get_stage(module_key, key):
    if not key:
        return None
    return WorkflowStage.objects.filter(module__key=module_key, key=key).first()


def first_stage(module_key):
    """The stage a brand-new requisition starts at, or None."""
    stages = get_stages(module_key)
    return stages[0] if stages else None


def next_stage(module_key, current_key):
    """The stage after ``current_key``, skipping inactive stages.

    Returns ``None`` once the chain is exhausted, which callers read as
    "nothing further to do".
    """
    stages = get_stages(module_key)
    keys = [s.key for s in stages]
    if current_key not in keys:
        return None
    index = keys.index(current_key)
    return stages[index + 1] if index + 1 < len(stages) else None


def stage_allows(stage, user):
    """Whether ``user`` may act at ``stage``.

    A stage with no ``approver_role`` is open to any approver, which keeps
    single-approver configurations simple. Otherwise the user's role must match,
    and the superadmin is always allowed so the portal can never deadlock.
    """
    if stage is None:
        return False
    if not user.is_authenticated:
        return False
    if user.is_admin():
        return True
    if not user.is_approver():
        return False
    if not stage.approver_role:
        return True
    return user.role == stage.approver_role


def pending_stages_for(module_key, user):
    """Stages this user can currently act on — drives the approver's work list.

    A user with no stage-specific role (a plain supervisor, say) can act on every
    stage whose role they satisfy, so this returns stages rather than a count.
    """
    return [s for s in get_stages(module_key) if stage_allows(s, user)]


def initial_status(module_key):
    stage = first_stage(module_key)
    return stage.key if stage else 'pending_first'


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------
def read_field_value(requisition, field):
    """Pull a field's value off a requisition, whether it is a column or JSON."""
    if field.is_system:
        return getattr(requisition, field.key, None)
    return (requisition.extra_data or {}).get(field.key, '')


def write_field_value(requisition, field, value):
    """Store a value on a requisition the same way ``read_field_value`` reads it."""
    if field.is_system:
        setattr(requisition, field.key, value)
    else:
        if requisition.extra_data is None:
            requisition.extra_data = {}
        requisition.extra_data[field.key] = value


def coerce_field_value(field, raw):
    """Turn a POST string into the python value for a system column.

    Returns ``(value, error)``. ``error`` is a human-readable message, or None.
    Unknown field types are stored as trimmed strings.
    """
    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else ''
    raw = (raw or '').strip()

    if field.field_type == 'checkbox':
        return raw in ('yes', 'true', 'on', '1'), None

    if not raw:
        return '', None

    try:
        if field.field_type == 'number':
            text = raw.replace(',', '')
            return (int(text) if text.lstrip('-').isdigit() else float(text)), None
        if field.field_type == 'date':
            from datetime import datetime
            return datetime.strptime(raw, '%Y-%m-%d').date(), None
        if field.field_type == 'time':
            from datetime import datetime
            return datetime.strptime(raw, '%H:%M').time(), None
        if field.field_type == 'datetime':
            from django.utils.dateparse import parse_datetime
            parsed = parse_datetime(raw)
            return (parsed, None) if parsed else (raw, None)
    except (TypeError, ValueError):
        return raw, f'Enter a valid {field.label.lower()}.'

    return raw, None


def validate_submission(module_key, posted):
    """Validate a raw POST dict against a module's configured fields.

    ``posted`` maps field key -> raw string (or list of strings for multi-value
    inputs). Returns ``(values, errors)`` where ``errors`` maps a field key to
    its first problem, so the template can mark each input inline.

    Values are coerced to python types, ready to be handed to the model.
    """
    fields = get_fields(module_key, only_visible=True)
    values, errors = {}, {}

    for field in fields:
        raw = posted.get(field.key)
        if isinstance(raw, (list, tuple)):
            raw = raw[0] if raw else ''
        raw = (raw or '').strip() if isinstance(raw, str) else raw

        if field.required and not raw:
            errors[field.key] = f'{field.label} is required.'
            continue

        value, error = coerce_field_value(field, raw)
        if error:
            errors[field.key] = error
            continue

        # Choice fields must match a configured option when one is set, so a
        # tampered POST cannot inject an arbitrary value.
        if field.option_list and value:
            allowed = {v for v, _ in field.option_list}
            if value not in allowed:
                errors[field.key] = f'Choose a valid {field.label.lower()}.'
                continue

        if field.field_type == 'email' and value:
            try:
                validate_email(value)
            except ValidationError:
                errors[field.key] = 'Enter a valid email address.'
                continue

        if field.field_type == 'number' and value != '':
            minimum = (field.config or {}).get('min')
            maximum = (field.config or {}).get('max')
            if minimum is not None and value < minimum:
                errors[field.key] = f'{field.label} must be at least {minimum}.'
                continue
            if maximum is not None and value > maximum:
                errors[field.key] = f'{field.label} must be at most {maximum}.'
                continue

        values[field.key] = value

    return values, errors


def validate_amendment(stage, posted):
    """Validate only the fields a stage is allowed to amend.

    Returns ``(changes, errors)``. ``changes`` maps field key -> coerced value
    and is deliberately restricted to the stage's ``amendable_fields``.
    """
    amendable = {f.key: f for f in stage.amendable_fields.all()}
    changes, errors = {}, {}

    for key, field in amendable.items():
        raw = (posted.get(key) or '').strip()
        if field.required and not raw:
            errors[key] = f'{field.label} is required.'
            continue
        if not raw:
            continue

        value, error = coerce_field_value(field, raw)
        if error:
            errors[key] = error
            continue
        if field.option_list and value not in {v for v, _ in field.option_list}:
            errors[key] = f'Choose a valid {field.label.lower()}.'
            continue
        changes[key] = value

    return changes, errors


def apply_changes(module_key, requisition, changes):
    """Write an amendment dict onto a requisition and report which keys moved.

    Only keys belonging to this module are honoured, so a crafted POST cannot
    touch another module's fields.
    """
    fields = {f.key: f for f in get_fields(module_key)}
    changed = []
    for key, value in changes.items():
        field = fields.get(key)
        if field is None:
            continue
        before = read_field_value(requisition, field)
        write_field_value(requisition, field, value)
        if str(before if before is not None else '') != str(value if value is not None else ''):
            changed.append(key)
    return changed


# For each module, which requisition attributes record that a stage was signed
# off. Keyed by stage key, mapping to (timestamp_field, actor_field). A stage
# with no entry here still shows as "current" on the track page, it just cannot
# display who signed it off or when.
STAGE_PROGRESS_FIELDS = {
    'transport': {
        'pending_first': (('first_approved_at', None), ('first_approver', None)),
        'pending_grants': (('grants_approved_at', None), ('grants_approver', None)),
        'pending_transport': (('transport_approved_at', None), ('transport_approver', None)),
    },
}


def audit_trail(module_key, requisition):
    """Build the ordered list of stages and whether the requisition passed each.

    Used by the track page so progress renders from configuration rather than a
    hardcoded list of statuses.
    """
    progress = STAGE_PROGRESS_FIELDS.get(module_key, {})
    passed = []
    for stage in get_stages(module_key):
        stamp_field, actor_field = progress.get(stage.key, (None, None))
        stamp = getattr(requisition, stamp_field, None) if stamp_field else None
        actor = getattr(requisition, actor_field, None) if actor_field else None
        passed.append({
            'stage': stage,
            'done': bool(stamp) or requisition.status == stage.key,
            'current': requisition.status == stage.key,
            'at': stamp,
            'by': actor,
        })
    return passed


# Re-exported so callers can do ``from portal_config.engine import StageAction``.
__all__ = [
    'StageAction', 'apply_changes', 'audit_trail', 'coerce_field_value',
    'enabled_module_keys', 'first_stage', 'get_fields', 'get_model',
    'get_module', 'get_stage', 'get_stages', 'initial_status', 'next_stage',
    'pending_stages_for', 'read_field_value', 'stage_allows',
    'validate_amendment', 'validate_submission', 'write_field_value',
]