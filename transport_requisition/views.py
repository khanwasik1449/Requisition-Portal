from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse
from datetime import date
import json
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from .models import TransportRequisition, Driver, Vehicle
from notifications.utils import send_approval_request, notify_requester, log_audit
from notifications.models import AuditLog
from portal_config import engine

# This module's key in portal_config / settings.ENABLED_MODULES. Every workflow
# decision below is read from configuration rather than hardcoded, so the
# Form Builder can change the chain without a code change.
MODULE = 'transport'

# Fields a public submitter must provide.
REQUIRED_FIELDS = (
    'full_name', 'email_address', 'mobile_number', 'designation', 'pin',
    'pick_up_date', 'pick_up_time', 'pick_up_location', 'destination',
    'drop_off_date', 'drop_off_time', 'drop_off_location', 'travelling_reason',
    'project_name_code', 'budget_code',
)

# Every field the form posts, so a failed submit can be redrawn with the user's
# own input instead of an empty page.
FORM_FIELDS = REQUIRED_FIELDS + (
    'num_passengers', 'vehicle_type', 'vehicle_type_other', 'comments_remarks',
)

# Human labels for validation messages, keyed by field name.
FIELD_LABELS = {
    'full_name': 'Your name',
    'email_address': 'Email address',
    'mobile_number': 'Mobile number',
    'designation': 'Designation',
    'pin': 'PIN',
    'pick_up_date': 'Pick-up date',
    'pick_up_time': 'Pick-up time',
    'pick_up_location': 'Pick-up location',
    'destination': 'Destination',
    'drop_off_date': 'Drop-off date',
    'drop_off_time': 'Drop-off time',
    'drop_off_location': 'Drop-off location',
    'travelling_reason': 'Reason for travelling',
    'num_passengers': 'Number of passengers',
    'vehicle_type_other': 'Vehicle type',
    'project_name_code': 'Project name and code',
    'budget_code': 'Budget code',
}

# Seating capacity per vehicle, used to warn about oversubscription.
VEHICLE_CAPACITY = {
    'sedan': 3,
    'noah': 7,
    'hiace_11': 11,
    'hiace_14': 14,
}

# Projects and the budget codes the Grants team issues against each, mirroring
# the official Google Form. Selecting a project narrows the budget list.
PROJECTS = [
    'Academic- M.ED (0002)',
    'Academic- ECD (0003)',
    'Academic- MHPSS (0056)',
    'Short Course- 0004',
    'Day Care Center- 0023',
    'SBCC- 0025',
    'Ayesha Abed Foundation- 0031',
    'VROOM Climate Change & Childcare Project- 0049',
    'ECDAN (142)- 0048',
    'PTL2.0 (143)- 0053',
    'BAINUM (144)- 0051',
    'HEAT (145)- 0052',
    'BRAC Play Lab (139)- 0041',
    'Save the Children- Step (146)- 0057',
    'Microfinance (147)- 0058',
]

PROJECT_BUDGETS = {
    'Academic- M.ED (0002)': ['0002-401010106', '0002-401010204', '0002-401030101'],
    'Academic- ECD (0003)': ['0003-401010106', '0003-401010204', '0003-401030101'],
    'Academic- MHPSS (0056)': ['0056-401010106', '0056-401010204', '0056-401030101'],
    'Short Course- 0004': ['0004-401030101'],
    'Day Care Center- 0023': ['0023-581111-04', '0023-581111-01'],
    'SBCC- 0025': ['0025-581111-04', '0025-581111-01'],
    'Ayesha Abed Foundation- 0031': ['0031-581111-01'],
    'VROOM Climate Change & Childcare Project- 0049': ['0049-570505-05', '0049-581111-01'],
    'ECDAN (142)- 0048': ['0048-581111-01', '0048-570505-05', '0048-581111-04'],
    'PTL2.0 (143)- 0053': ['0053-581111-01'],
    'BAINUM (144)- 0051': ['0051-402010703', '0051-581111-04'],
    'HEAT (145)- 0052': ['0052-402010701'],
    'BRAC Play Lab (139)- 0041': ['0041-581111-04', '0041-581111-01'],
    'Save the Children- Step (146)- 0057': ['0057-581212-01'],
    'Microfinance (147)- 0058': ['0058-581111-01', '0058-570505-05'],
}

# Shown on the form, mirroring the help text on the official Google Form.
SAFETY_NOTES = [
    "Fasten your seat belt.",
    "Do not gossip with the driver — it distracts them from driving.",
    "Do not instruct the driver on how to drive.",
    "Do not smoke in the vehicle.",
    "Do not speak loudly.",
    "Do not ask the driver to play music or video.",
    "Take a 10–15 minute break every 2 hours on long journeys.",
    "Avoid travelling at midnight or straight after lunch unless it is an emergency.",
    "Insist the driver follows the BRAC speed limit.",
    "Behave in a gender-friendly manner.",
]

VENDOR_NOTES = [
    'Every vehicle carries a log sheet — collect it from the driver before you set off.',
    'Note the start and end kilometre reading and time on the log sheet, then sign it '
    'with your name and PIN.',
]

TRANSPORT_HELP_EMAIL = 'ashfikur.rahman@bracu.ac.bd'
TRANSPORT_HELP_PHONE = '+8801913388942'

# The form is filled one section at a time. This maps each field to the step it
# lives on, so a failed submit can jump the user straight back to the step that
# needs fixing instead of showing every problem at once.
STEP_FIELDS = (
    ('full_name', 'email_address', 'mobile_number', 'designation', 'pin', 'num_passengers'),
    ('vehicle_type', 'vehicle_type_other',
     'pick_up_date', 'pick_up_time', 'pick_up_location', 'destination',
     'drop_off_date', 'drop_off_time', 'drop_off_location'),
    ('travelling_reason', 'project_name_code'),
    ('budget_code',),
    ('supervisor_acknowledged', 'comments_remarks'),
)

STEP_TITLES = (
    'Information',
    'Vehicle and Trip',
    'Trip Details and Reason',
    'Select Budget Code',
    'Supervisor and Remarks',
)


def build_form_context(base_template, actor, posted, errors, summary=None, today='', start_step=1):
    """Assemble everything the transport form template needs.

    The step list is derived from the FormField rows rather than STEP_TITLES, so
    an administrator regrouping a field onto another step moves it on the live
    form immediately. STEP_TITLES is only consulted for step captions that have
    no explicit title stored on the field rows.
    """
    fields = list(engine.get_fields(MODULE, only_visible=True))

    steps = []
    for field in fields:
        step_number = field.step or 1
        while len(steps) < step_number:
            index = len(steps)
            steps.append({
                'number': index + 1,
                'title': STEP_TITLES[index] if index < len(STEP_TITLES) else f'Step {index + 1}',
                'fields': [],
            })
        steps[step_number - 1]['fields'].append(field)

    # Drop any steps an administrator emptied out.
    steps = [s for s in steps if s['fields']]

    return {
        'base_template': base_template,
        'posted': posted or {},
        'errors': errors or {},
        'summary': summary,
        'today': today or timezone.now().date().isoformat(),
        'prefill_email': actor.email if actor else '',
        'prefill_name': actor.get_full_name() if actor else '',
        'projects': PROJECTS,
        'all_budget_codes': sorted({c for codes in PROJECT_BUDGETS.values() for c in codes}),
        'project_budgets': json.dumps(PROJECT_BUDGETS),
        'steps': steps,
        'step_titles': [s['title'] for s in steps],
        'step_count': len(steps),
        'start_step': start_step or 1,
        'safety_notes': SAFETY_NOTES,
        'vendor_notes': VENDOR_NOTES,
        'help_email': TRANSPORT_HELP_EMAIL,
        'help_phone': TRANSPORT_HELP_PHONE,
    }


@login_required
def list_view(request):
    """The signed-in work list.

    Admins and the transport admin see everything. Anyone else sees the
    requisitions sitting at a stage they are allowed to act on, plus their own.
    """
    if request.user.is_admin() or request.user.is_transport_admin():
        requisitions = TransportRequisition.objects.all()
    else:
        actionable = [
            s.key for s in engine.pending_stages_for(MODULE, request.user)
            if not s.is_terminal
        ]
        waiting = TransportRequisition.objects.none()
        if actionable:
            waiting = TransportRequisition.objects.filter(status__in=actionable)
        requisitions = (waiting | TransportRequisition.objects.filter(user=request.user)).distinct()

    stages = engine.get_stages(MODULE)
    # Stages this particular user may act on right now, for the action buttons.
    my_stages = {
        s.key: s for s in engine.pending_stages_for(MODULE, request.user)
        if not s.is_terminal
    }
    return render(request, 'transport_requisition/list.html', {
        'requisitions': requisitions,
        'stages': stages,
        'stage_by_key': {s.key: s for s in stages},
        'my_stage_keys': my_stages,
    })


def first_error_step(errors):
    """1-based index of the earliest step that has a problem, else None."""
    if not errors:
        return None
    for index, fields in enumerate(STEP_FIELDS, start=1):
        if any(field in errors for field in fields):
            return index
    return None


def create_view(request):
    """Public request form — no login required.

    Signed-in users get the full app chrome; anonymous visitors get the plain
    public layout. Both store identical records; `user` is simply null for
    anonymous submissions.
    """
    is_auth = request.user.is_authenticated
    actor = request.user if is_auth else None
    base_template = 'base.html' if is_auth else 'base_public.html'

    if request.method == 'POST':
        errors = {}

        def fail(field, message):
            """Record the first problem per field so the UI can mark it inline."""
            errors.setdefault(field, message)

        # Use .get() throughout: this endpoint is public, so never assume keys.
        posted = {k: (request.POST.get(k) or '').strip() for k in FORM_FIELDS}
        for field in engine.get_fields(MODULE, only_visible=True):
            posted.setdefault(field.key, (request.POST.get(field.key) or '').strip())
        posted['supervisor_acknowledged'] = request.POST.get('supervisor_acknowledged') == 'yes'

        # Required / type / choice checking now comes from the field definitions
        # an administrator maintains in the Form Builder.
        values, field_errors = engine.validate_submission(MODULE, request.POST)
        errors.update(field_errors)

        mobile = posted.get('mobile_number', '').replace(' ', '').replace('-', '')
        if mobile and not (mobile.isdigit() and 7 <= len(mobile) <= 15):
            fail('mobile_number', 'Enter a valid mobile number (7 to 15 digits).')

        if posted.get('pin') and not posted['pin'].isdigit():
            fail('pin', 'PIN should contain digits only.')

        vehicle_type = posted.get('vehicle_type') or TransportRequisition.VehicleType.SEDAN
        if vehicle_type == 'other' and not posted.get('vehicle_type_other'):
            fail('vehicle_type_other', 'Tell us which vehicle you need.')

        # Dates must be real and in order. Compared as strings because both
        # arrive as ISO yyyy-mm-dd from <input type="date">.
        today = timezone.now().date().isoformat()
        for field in ('pick_up_date', 'drop_off_date'):
            value = posted.get(field)
            if not value:
                continue
            try:
                year, month, day = (int(p) for p in value.split('-'))
                date(year, month, day)
            except (TypeError, ValueError):
                fail(field, 'Enter a valid date.')
            if value < today and field == 'pick_up_date':
                fail(field, 'Pick-up date cannot be in the past.')

        pickup_date, dropoff_date = posted.get('pick_up_date', ''), posted.get('drop_off_date', '')
        pickup_time, dropoff_time = posted.get('pick_up_time', ''), posted.get('drop_off_time', '')
        if (not errors.get('drop_off_date') and not errors.get('pick_up_date')
                and dropoff_date and pickup_date and dropoff_date < pickup_date):
            fail('drop_off_date', 'Drop-off date cannot be before the pick-up date.')
        elif (not errors.get('drop_off_time') and not errors.get('pick_up_time')
              and dropoff_date and pickup_date and dropoff_date == pickup_date
              and dropoff_time and pickup_time and dropoff_time < pickup_time):
            fail('drop_off_time', 'Drop-off time cannot be before the pick-up time.')

        if errors:
            summary = 'Please fix the highlighted fields and submit again.'
            for message in errors.values():
                messages.error(request, message)
            return render(request, 'transport_requisition/form.html', build_form_context(
                base_template=base_template, actor=actor, posted=posted,
                errors=errors, summary=summary, today=today,
                start_step=first_error_step(errors),
            ), status=400)

        requisition = TransportRequisition(user=actor)
        # Write every configured field onto the model. Fields an administrator
        # added land in extra_data, so this loop needs no per-field code.
        for field in engine.get_fields(MODULE, only_visible=True):
            engine.write_field_value(requisition, field, values.get(field.key, ''))
        requisition.vehicle_type = vehicle_type
        requisition.num_passengers = values.get('num_passengers') or 1
        requisition.status = engine.initial_status(MODULE)
        requisition.save()

        log_audit(
            'transport', requisition.pk, requisition.request_number, 'created', actor,
            f'Public form submission by {requisition.full_name} <{requisition.email_address}>'
            if not is_auth else 'Submitted by signed-in user',
        )
        send_approval_request('transport', requisition, MODULE, requisition.status)
        notify_requester('transport', requisition, MODULE, 'created')

        if is_auth:
            return redirect('transport_requisition:list')
        return render(request, 'transport_requisition/submitted.html', {'r': requisition})

    # Pre-fill for signed-in users. Done here rather than in the template
    # because `request.user` is an AnonymousUser for public visitors, which has
    # no get_full_name().
    actor = request.user if is_auth else None
    return render(request, 'transport_requisition/form.html', build_form_context(
        base_template=base_template, actor=actor, posted=None, errors=None,
        today=timezone.now().date().isoformat(), start_step=1,
    ))


def track_view(request):
    """Public self-service status lookup by email address.

    Returns only requests whose email_address matches exactly (case-insensitive),
    so this cannot be used to enumerate other people's requests.
    """
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        if not email:
            messages.error(request, 'Please enter the email address you used.')
            return render(request, 'transport_requisition/track.html',
                          {'searched': False}, status=400)
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Enter a valid email address.')
            return render(request, 'transport_requisition/track.html',
                          {'searched': False}, status=400)

        stage_by_key = {s.key: s for s in engine.get_stages(MODULE)}
        return render(request, 'transport_requisition/track.html', {
            'searched': True,
            'email': email,
            'requisitions': TransportRequisition.objects.filter(email_address__iexact=email),
            'stage_by_key': stage_by_key,
        })

    return render(request, 'transport_requisition/track.html', {'searched': False})


@login_required
def history_view(request):
    """Admin-only tracking history: every request plus its audit trail."""
    if not (request.user.is_admin() or request.user.is_transport_admin()):
        messages.error(request, 'Access denied. Admin only.')
        return redirect('transport_requisition:list')

    qs = TransportRequisition.objects.all()
    search = (request.GET.get('q') or '').strip()
    status_filter = request.GET.get('status') or ''
    date_from = request.GET.get('date_from') or ''
    date_to = request.GET.get('date_to') or ''

    if search:
        qs = qs.filter(Q(email_address__icontains=search)
                       | Q(full_name__icontains=search)
                       | Q(request_number__icontains=search)
                       | Q(pin__icontains=search)
                       | Q(destination__icontains=search))
    if status_filter:
        qs = qs.filter(status=status_filter)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    requisitions = list(qs)
    # Pull the audit trail for exactly this result set in a single query, then
    # attach it to each object so the template can iterate directly.
    trail = {}
    if requisitions:
        for entry in AuditLog.objects.filter(
                req_type='transport', req_id__in=[r.pk for r in requisitions]).order_by('created_at'):
            trail.setdefault(entry.req_id, []).append(entry)
    for r in requisitions:
        r.trail = trail.get(r.pk, [])

    stage_by_key = {s.key: s for s in engine.get_stages(MODULE)}
    return render(request, 'transport_requisition/history.html', {
        'requisitions': requisitions,
        'search': search,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'Status': TransportRequisition.Status,
        'stages': list(stage_by_key.values()),
        'stage_by_key': stage_by_key,
        'counts': {
            'total': TransportRequisition.objects.count(),
            'pending': TransportRequisition.objects.filter(
                status__in=TransportRequisition.PENDING_STATUSES).count(),
            'approved': TransportRequisition.objects.filter(
                status__in=[TransportRequisition.Status.APPROVED,
                            TransportRequisition.Status.ASSIGNED]).count(),
            'rejected': TransportRequisition.objects.filter(
                status=TransportRequisition.Status.REJECTED).count(),
            'public': TransportRequisition.objects.filter(user__isnull=True).count(),
        },
    })


@login_required
def detail_view(request, pk):
    requisition = get_object_or_404(TransportRequisition, pk=pk)
    if not (request.user.is_admin() or request.user.is_approver() or requisition.user == request.user):
        return redirect('transport_requisition:list')

    stage = engine.get_stage(MODULE, requisition.status)
    can_act = stage is not None and not stage.is_terminal and engine.stage_allows(stage, request.user)
    stages = engine.get_stages(MODULE)
    return render(request, 'transport_requisition/detail.html', {
        'r': requisition,
        'stage': stage,
        'can_act': can_act,
        'stages': stages,
        'stage_by_key': {s.key: s for s in stages},
        'trail': engine.audit_trail(MODULE, requisition),
        'amendable_fields': list(stage.amendable_fields.all()) if (can_act and stage.can_amend) else [],
    })


def _stamp_stage(requisition, stage, user):
    """Record who signed off a stage and when, on the columns that track it.

    A stage with no dedicated columns (or a module that never wired them up) is
    skipped silently, so adding a stage to the configuration cannot crash the
    approval that is passing through it.
    """
    mapping = {
        'pending_first': ('first_approver', 'first_approved_at'),
        'pending_grants': ('grants_approver', 'grants_approved_at'),
        'pending_transport': ('transport_approver', 'transport_approved_at'),
    }
    if stage.key not in mapping:
        return timezone.now()

    actor_field, stamp_field = mapping[stage.key]
    if not hasattr(requisition, actor_field) or not hasattr(requisition, stamp_field):
        return timezone.now()

    now = timezone.now()
    setattr(requisition, actor_field, user)
    setattr(requisition, stamp_field, now)
    return now


def _advance(requisition, stage, user, details=''):
    """Move a requisition past ``stage`` to the next one and notify everyone.

    Called after the stage's decision has been applied. Records the sign-off,
    walks to the next configured stage, writes the audit entry, and emails the
    next approver and the requester.
    """
    _stamp_stage(requisition, stage, user)

    following = engine.next_stage(MODULE, stage.key)
    if following is None:
        # Chain exhausted: treat the approved stage itself as final.
        following = engine.get_stage(MODULE, 'assigned')
    requisition.status = following.key if following else TransportRequisition.Status.APPROVED
    requisition.save()

    log_audit('transport', requisition.pk, requisition.request_number,
              stage.key, user, details)
    send_approval_request('transport', requisition, MODULE, requisition.status)
    notify_requester('transport', requisition, MODULE, requisition.status)
    return requisition


@login_required
def approve_view(request, pk):
    """Approve the requisition at whatever stage it is currently sitting at.

    The chain itself comes from configuration, so this view does not need to
    know that Grants sits between the supervisor and the transport admin.
    """
    requisition = get_object_or_404(TransportRequisition, pk=pk)
    stage = engine.get_stage(MODULE, requisition.status)

    if stage is None:
        messages.error(request, 'This requisition is not awaiting approval.')
        return redirect('transport_requisition:detail', pk=requisition.pk)
    if not engine.stage_allows(stage, request.user):
        messages.error(request, f'You are not authorised to act at "{stage.name}".')
        return redirect('transport_requisition:detail', pk=requisition.pk)
    if not stage.can_approve:
        messages.error(request, f'"{stage.name}" does not allow approval.')
        return redirect('transport_requisition:detail', pk=requisition.pk)

    # A stage flagged 'amend' may also correct its fields on the way through.
    amend_details = ''
    if stage.can_amend:
        changes, errors = engine.validate_amendment(stage, request.POST)
        if errors:
            for message in errors.values():
                messages.error(request, message)
            return redirect('transport_requisition:detail', pk=requisition.pk)
        changed = engine.apply_changes(MODULE, requisition, changes)
        if changed:
            remark = (request.POST.get('remarks') or '').strip()
            requisition.grants_remarks = remark
            requisition.grants_amended = True
            amend_details = 'Amended ' + ', '.join(
                f'{key}: {changes[key]}' for key in changed
            )

    _advance(requisition, stage, request.user, amend_details)
    messages.success(request, f'Approved at "{stage.name}".')
    return redirect('transport_requisition:list')


@login_required
def reject_view(request, pk):
    """Decline the requisition, with a reason the requester is emailed."""
    requisition = get_object_or_404(TransportRequisition, pk=pk)
    stage = engine.get_stage(MODULE, requisition.status)

    if stage is None or stage.is_terminal:
        messages.error(request, 'This requisition is no longer pending approval.')
        return redirect('transport_requisition:detail', pk=requisition.pk)
    if not engine.stage_allows(stage, request.user):
        messages.error(request, f'You are not authorised to act at "{stage.name}".')
        return redirect('transport_requisition:detail', pk=requisition.pk)
    if not stage.can_decline:
        messages.error(request, f'"{stage.name}" does not allow declining.')
        return redirect('transport_requisition:detail', pk=requisition.pk)

    if request.method == 'POST':
        reason = (request.POST.get('reason') or '').strip()
        if not reason and stage.require_reason_on_decline:
            messages.error(request, 'Please give a reason so the requester knows what to fix.')
            return redirect('transport_requisition:reject', pk=requisition.pk)

        _stamp_stage(requisition, stage, request.user)
        requisition.status = TransportRequisition.Status.REJECTED
        requisition.rejection_reason = reason
        requisition.rejected_at = timezone.now()
        requisition.save()

        log_audit('transport', requisition.pk, requisition.request_number,
                  'rejected', request.user, f'{stage.name}: {reason}')
        notify_requester('transport', requisition, MODULE, 'rejected')
        messages.success(request, f'Declined at "{stage.name}".')
        return redirect('transport_requisition:list')

    return render(request, 'transport_requisition/reject.html', {
        'r': requisition,
        'stage': stage,
    })


@login_required
def report_view(request):
    if not (request.user.is_admin() or request.user.is_transport_admin()):
        return redirect('transport_requisition:list')

    qs = TransportRequisition.objects.all()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status_filter = request.GET.get('status', '')

    if date_from:
        qs = qs.filter(pick_up_date__gte=date_from)
    if date_to:
        qs = qs.filter(pick_up_date__lte=date_to)
    if status_filter:
        qs = qs.filter(status=status_filter)

    total = qs.count()
    approved = qs.filter(status__in=[
        TransportRequisition.Status.APPROVED,
        TransportRequisition.Status.ASSIGNED,
    ]).count()
    rejected = qs.filter(status=TransportRequisition.Status.REJECTED).count()
    pending = qs.filter(status__in=TransportRequisition.PENDING_STATUSES).count()

    stage_by_key = {s.key: s for s in engine.get_stages(MODULE)}
    return render(request, 'transport_requisition/report.html', {
        'requisitions': qs,
        'total': total,
        'approved': approved,
        'rejected': rejected,
        'pending': pending,
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
        'Status': TransportRequisition.Status,
        'stages': list(stage_by_key.values()),
        'stage_by_key': stage_by_key,
    })


@login_required
def export_excel_view(request):
    if not (request.user.is_admin() or request.user.is_transport_admin()):
        return redirect('transport_requisition:list')

    qs = TransportRequisition.objects.all()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status_filter = request.GET.get('status', '')

    if date_from:
        qs = qs.filter(pick_up_date__gte=date_from)
    if date_to:
        qs = qs.filter(pick_up_date__lte=date_to)
    if status_filter:
        qs = qs.filter(status=status_filter)

    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Transport Requisitions'

    headers = ['Request #', 'Name', 'Email', 'Mobile', 'Designation', 'PIN', 'Passengers',
               'Vehicle Type', 'Pick-up Date', 'Pick-up Time', 'Pick-up Location',
               'Destination', 'Drop-off Date', 'Drop-off Time', 'Drop-off Location',
               'Travelling Reason', 'Project Name/Code', 'Budget Code',
               'Driver', 'Car No', 'Driver Cell', 'Status']

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = openpyxl.styles.PatternFill(start_color='D97706', end_color='D97706', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border

    for row, r in enumerate(qs, 2):
        data = [
            r.request_number, r.full_name, r.email_address, r.mobile_number, r.designation, r.pin,
            r.num_passengers, r.get_vehicle_type_display(),
            r.pick_up_date, str(r.pick_up_time), r.pick_up_location,
            r.destination, r.drop_off_date, str(r.drop_off_time), r.drop_off_location,
            r.travelling_reason, r.project_name_code, r.budget_code,
            r.driver.name if r.driver else '', r.driver.car_no if r.driver else '',
            r.driver.cell_number if r.driver else '',
            r.get_status_display()
        ]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.border = thin_border

    for col in range(1, len(headers) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 18

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="transport_requisitions_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    wb.save(response)
    return response


@login_required
def assign_driver_view(request, pk):
    """Transport admin allocates a vehicle and driver, then notifies the requester.

    This is the 'assign' action on the transport-admin stage, so it is reachable
    only while the requisition is at that stage.
    """
    requisition = get_object_or_404(TransportRequisition, pk=pk)
    stage = engine.get_stage(MODULE, requisition.status)
    assign_stage = next(
        (s for s in engine.get_stages(MODULE) if s.can_assign),
        None,
    )

    if stage is None:
        messages.error(request, 'This requisition is not awaiting assignment.')
        return redirect('transport_requisition:detail', pk=requisition.pk)
    if not engine.stage_allows(stage, request.user):
        messages.error(request, f'You are not authorised to act at "{stage.name}".')
        return redirect('transport_requisition:detail', pk=requisition.pk)
    if not stage.can_assign or assign_stage is None:
        messages.error(request, f'"{stage.name}" does not allow assigning a vehicle.')
        return redirect('transport_requisition:detail', pk=requisition.pk)

    drivers = Driver.objects.all()
    vehicles = Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE)

    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle')
        driver_id = request.POST.get('driver')
        if not vehicle_id or not driver_id:
            messages.error(request, 'Choose both a vehicle and a driver.')
            return redirect('transport_requisition:assign_driver', pk=requisition.pk)

        requisition.vehicle_id = vehicle_id
        requisition.driver_id = driver_id
        requisition.assigned_by = request.user
        requisition.assigned_at = timezone.now()
        requisition.save()

        # Move on to the terminal 'assigned' stage so the requester's tracking
        # page shows the trip as confirmed rather than still in progress.
        following = engine.next_stage(MODULE, stage.key)
        requisition.status = following.key if following else TransportRequisition.Status.ASSIGNED
        requisition.save()

        log_audit('transport', requisition.pk, requisition.request_number,
                  'assigned', request.user,
                  f'{requisition.vehicle.registration_number} / {requisition.driver.name}')
        notify_requester('transport', requisition, MODULE, 'driver_assigned')
        messages.success(request, 'Vehicle and driver assigned. The requester has been notified.')
        return redirect('transport_requisition:detail', pk=requisition.pk)

    return render(request, 'transport_requisition/assign_driver.html', {
        'r': requisition,
        'stage': stage,
        'drivers': drivers,
        'vehicles': vehicles,
    })
