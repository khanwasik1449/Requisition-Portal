"""Admin screens for editing form fields and approval workflows.

Restricted to the superadmin and the transport admin, per the portal's
configuration policy. Everything here writes rows that ``engine`` reads at
request time, so changes take effect on the next page load with no restart.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import clear_url_caches

from accounts.models import User
from .engine import get_fields, get_model, get_module, get_stages
from .models import FieldType, FormField, Module, StageAction, WorkflowStage

# Everyone who may reshape the portal's forms and workflows.
CONFIG_ROLES = ('admin', 'transport_admin')

VALID_ACTIONS = {a.value for a in StageAction}


def _may_configure(user):
    """Superadmin or transport admin. Kept in one place so every view agrees."""
    return user.is_authenticated and (
        user.is_admin() or user.is_transport_admin()
    )


def _guard(request):
    """Return True when the user may configure; otherwise redirect and return False."""
    if _may_configure(request.user):
        return True
    messages.error(request, 'You do not have permission to configure the portal.')
    return False


@login_required
def module_list(request):
    if not _guard(request):
        return redirect('dashboard')

    # Only the superadmin may switch modules on or off. The transport admin can
    # edit fields and workflows, but not decide which modules exist.
    is_super = request.user.is_admin()

    modules = []
    for module in Module.objects.filter(is_active=True).order_by('order', 'name'):
        modules.append({
            'module': module,
            'fields': module.fields.count(),
            'stages': list(module.stages.order_by('order', 'id')),
            'enabled': module.is_enabled,
            'visible': module.is_visible,
        })
    return render(request, 'portal_config/module_list.html', {
        'modules': modules,
        'all_modules': list(Module.objects.order_by('order', 'name')),
        'configured_modules': {entry['module'].key for entry in modules},
        'is_super': is_super,
    })


@login_required
def module_toggle(request, module_key):
    """Switch a module on/off or show/hide it.

    Two independent flags, posted as separate checkboxes:

    ``enabled``  -- hard switch. Off means the module is not routed: its URLs
                   404 and its data is unreachable from the portal.
    ``visible`` -- soft switch. Off means the module stays routed and its data
                   is intact, but it disappears from the nav, dashboard and
                   "My Requisitions".

    Restricted to the superadmin. Changes take effect on the next request; the
    URL conf is rebuilt per request, so no restart is needed.
    """
    if not request.user.is_admin():
        messages.error(request, 'Only the superadmin can switch modules on or off.')
        return redirect('portal_config:module_list')

    module = get_module(module_key)
    if not module:
        messages.error(request, f'Unknown module "{module_key}".')
        return redirect('portal_config:module_list')

    if request.method != 'POST':
        return redirect('portal_config:module_list')

    module.is_enabled = 'enabled' in request.POST
    module.is_visible = 'visible' in request.POST
    # Turning a module back on also shows it again: the two checkboxes cannot
    # distinguish "left away" from "unticked", so an explicit re-enable is the
    # only moment we can safely assume the user wants it visible. Turning a
    # module off always hides it, since a hidden-but-routed module is
    # indistinguishable from an off one to anyone using the portal.
    if module.is_enabled and 'visible' not in request.POST:
        module.is_visible = True
    if not module.is_enabled:
        module.is_visible = False
    module.save()

    # Django caches the URL conf per worker process, so the new routing only
    # reaches requests served by this worker until the cache is dropped.
    clear_url_caches()

    state = 'on' if module.is_enabled else 'off'
    shown = 'visible' if module.is_visible else 'hidden'
    messages.success(request, f'{module.name} is now {state} and {shown}.')
    return redirect('portal_config:module_list')


@login_required
def field_list(request, module_key):
    """Every field on a module's form, ordered the way it renders."""
    if not _guard(request):
        return redirect('dashboard')

    module = get_module(module_key)
    if not module:
        messages.error(request, f'Unknown module "{module_key}".')
        return redirect('portal_config:module_list')

    fields = get_fields(module_key)
    steps = {}
    for field in fields:
        steps.setdefault(field.step, []).append(field)
    step_numbers = sorted(steps)

    return render(request, 'portal_config/field_list.html', {
        'module': module,
        'fields': fields,
        'steps': [(n, steps[n]) for n in step_numbers],
        'field_types': FieldType.choices,
    })


@login_required
def field_edit(request, module_key, pk=None):
    """Create or edit a single form field."""
    if not _guard(request):
        return redirect('dashboard')

    module = get_module(module_key)
    if not module:
        messages.error(request, f'Unknown module "{module_key}".')
        return redirect('portal_config:module_list')

    field = get_object_or_404(FormField, pk=pk, module=module) if pk else FormField(module=module)

    if request.method == 'POST':
        form = _field_form(request.POST, field)
        if form.is_valid():
            saved = form.save()
            messages.success(
                request,
                f'Field "{saved.label}" saved. It is live on the {module.name} form now.',
            )
            return redirect('portal_config:field_list', module_key=module_key)
        messages.error(request, 'Please correct the highlighted fields.')
    else:
        form = _field_form(None, field)

    return render(request, 'portal_config/field_edit.html', {
        'module': module,
        'form': form,
        'field': field,
        'is_new': pk is None,
    })


def _field_form(data, instance):
    """Light validation around a FormField, kept explicit for readable errors."""
    from django import forms

    class FieldForm(forms.ModelForm):
        class Meta:
            model = FormField
            fields = (
                'label', 'key', 'field_type', 'help_text', 'placeholder',
                'step', 'order', 'required', 'is_system',
                'visible_to_requester', 'show_in_review', 'options',
            )

        def clean_key(self):
            key = self.cleaned_data['key'].strip().lower().replace(' ', '_').replace('-', '_')
            if not key.replace('_', '').isalnum():
                raise forms.ValidationError(
                    'Use letters, numbers and underscores only (e.g. cost_centre).'
                )
            return key

        def clean(self):
            cleaned = super().clean()
            # "Store in a database column" is only valid for a key the
            # requisition model actually has. Anything else has to go into the
            # extra_data JSON blob, which is what makes admin-added fields work
            # without a migration.
            key = cleaned.get('key')
            if not key or not self.instance.module_id or not cleaned.get('is_system'):
                return cleaned

            known = set(
                FormField.objects.filter(
                    module=self.instance.module, is_system=True
                ).values_list('key', flat=True)
            )
            if key not in known and not _module_has_column(self.instance.module.key, key):
                self.add_error(
                    'is_system',
                    f'"{key}" is not a column on the requisition model. '
                    'Untick this box to keep the value in the extra data '
                    'field instead — the form will still work.',
                )
            return cleaned

    return FieldForm(data, instance=instance)


def _module_has_column(module_key, field_key):
    """Whether the requisition model backing a module has a matching attribute."""
    model = get_model(module_key)
    return model is not None and hasattr(model, field_key)


@login_required
def field_delete(request, module_key, pk):
    if not _guard(request):
        return redirect('dashboard')

    field = get_object_or_404(FormField, pk=pk, module__key=module_key)
    if request.method == 'POST':
        label = field.label
        field.delete()
        messages.success(request, f'Removed "{label}" from the form.')
        return redirect('portal_config:field_list', module_key=module_key)
    return render(request, 'portal_config/confirm_delete.html', {
        'module': get_module(module_key),
        'object_label': field.label,
        'action_url': f'/portal-config/{module_key}/fields/{pk}/delete/',
    })


@login_required
def workflow(request, module_key):
    """Edit a module's approval chain.

    Rendered as one form per stage so a whole chain can be saved in a single
    submission, which keeps the live workflow from ever being half-updated.
    """
    if not _guard(request):
        return redirect('dashboard')

    module = get_module(module_key)
    if not module:
        messages.error(request, f'Unknown module "{module_key}".')
        return redirect('portal_config:module_list')

    stages = get_stages(module_key)
    all_fields = get_fields(module_key)

    if request.method == 'POST':
        return _save_workflow(request, module, stages, all_fields)

    # Pair each stage with the field ids it may amend, so the template does not
    # need a custom filter to do the lookup.
    stage_rows = [
        {
            'stage': stage,
            'amendable_pks': set(stage.amendable_fields.values_list('pk', flat=True)),
            'action_set': stage.action_set,
        }
        for stage in stages
    ]

    return render(request, 'portal_config/workflow.html', {
        'module': module,
        'stage_rows': stage_rows,
        'all_fields': all_fields,
        'role_choices': User.Role.choices,
        'actions': [(a.value, a.label) for a in StageAction],
    })


def _save_workflow(request, module, stages, all_fields):
    """Persist the whole chain, then return the user to the editor."""
    by_pk = {s.pk: s for s in stages}
    errors = []

    for pk, stage in by_pk.items():
        prefix = f'stage-{pk}-'
        if f'{prefix}delete' in request.POST:
            if len(stages) <= 1:
                errors.append('A workflow needs at least one stage.')
            else:
                stage.delete()
            continue

        stage.name = (request.POST.get(f'{prefix}name') or '').strip() or stage.name
        stage.approver_role = request.POST.get(f'{prefix}role') or ''
        if stage.approver_role and stage.approver_role not in dict(User.Role.choices):
            errors.append(f'"{stage.name}": "{stage.approver_role}" is not a known role.')
        stage.is_terminal = f'{prefix}terminal' in request.POST
        stage.is_active = f'{prefix}active' in request.POST

        actions = [
            a.strip() for a in (request.POST.get(f'{prefix}actions') or '').split(',')
            if a.strip()
        ]
        bad = [a for a in actions if a not in VALID_ACTIONS]
        if bad:
            # Do not persist a chain we could not act on -- the stage would
            # silently stop offering approve/decline at runtime.
            errors.append(
                f'"{stage.name}": unknown action(s) {", ".join(bad)}. '
                f'Valid actions are: {", ".join(sorted(VALID_ACTIONS))}.'
            )
        else:
            stage.actions = ','.join(actions)
        stage.save()

        chosen = request.POST.getlist(f'{prefix}amend')
        valid_pks = {f.pk for f in all_fields}
        stage.amendable_fields.set(
            [int(pk) for pk in chosen if str(pk).isdigit() and int(pk) in valid_pks]
        )

    # Reorder by whatever the user typed, so the rail can be rearranged freely.
    for pk in request.POST.getlist('stage-order'):
        stage = by_pk.get(int(pk)) if str(pk).isdigit() else None
        if stage:
            stage.order = request.POST.getlist('stage-order').index(pk) + 1
            stage.save()

    if errors:
        for message in errors:
            messages.error(request, message)
    else:
        messages.success(request, f'{module.name} workflow saved. It applies to new requisitions immediately.')
    return redirect('portal_config:workflow', module_key=module.key)


@login_required
def workflow_add_stage(request, module_key):
    if not _guard(request):
        return redirect('dashboard')

    module = get_module(module_key)
    if not module:
        messages.error(request, f'Unknown module "{module_key}".')
        return redirect('portal_config:module_list')

    last = module.stages.order_by('-order').first()
    stage = WorkflowStage.objects.create(
        module=module,
        key=f'stage_{module.stages.count() + 1}_{int(now_ts())}',
        name='New stage',
        order=(last.order + 1) if last else 1,
        approver_role='supervisor',
        actions='approve,decline',
    )
    messages.success(
        request,
        f'Added "{stage.name}". Give it a key in the URL-safe format, then save the workflow.',
    )
    return redirect('portal_config:workflow', module_key=module_key)


def now_ts():
    import time
    return int(time.time())