"""Approval-workflow helpers backing the React frontend.

The Django template views already implement the real approval chains. Rather
than reimplementing them and drifting apart, everything here calls the very
same ``portal_config.engine`` primitives and ``notifications.utils``
side-effects those views use, so a decision made through
``/api/transport/{pk}/approve/`` behaves exactly like the same decision made by
posting the original form.

Each ``*_context`` helper mirrors the context dict its template view passes to
``render``; each ``*_approve`` / ``*_decline`` helper mirrors the matching
``*_view``. When main's view prints ``messages.error(...)`` and redirects, the
equivalent here raises :class:`WorkflowError`, which the viewset turns into a
400 (or 403) carrying the same sentence.
"""

from django.utils import timezone

from notifications.utils import log_audit, notify_requester, send_approval_request
from portal_config import engine
from transport_requisition.models import Driver, TransportRequisition, Vehicle
from transport_requisition.views import MODULE as TRANSPORT_MODULE, _advance, _stamp_stage


class WorkflowError(Exception):
    """A decision the API refuses, carrying the message shown to the user."""

    def __init__(self, message, http_status=400):
        super().__init__(message)
        self.message = message
        self.http_status = http_status


def _error(message, http_status=400):
    return {'error': message}, http_status


# ---------------------------------------------------------------------------
# Serialization shared by the "which buttons do I show?" endpoint
# ---------------------------------------------------------------------------
def stage_info(stage):
    """The workflow stage's capabilities, in the shape the detail page wants."""
    if stage is None:
        return None
    return {
        'key': stage.key,
        'name': stage.name,
        'can_approve': stage.can_approve,
        'can_decline': stage.can_decline,
        'can_assign': stage.can_assign,
        'can_amend': stage.can_amend,
        'require_reason_on_decline': stage.require_reason_on_decline,
        'is_terminal': stage.is_terminal,
        'approver_role': stage.approver_role,
    }


def amendable_fields_for(requisition, stage):
    """Fields this stage is permitted to correct, each with its current value."""
    if stage is None or not stage.can_amend:
        return []
    return [
        {
            'key': field.key,
            'label': field.label,
            'input_type': field.input_type,
            'required': field.required,
            'placeholder': field.placeholder,
            'options': [
                {'value': value, 'label': label} for value, label in field.option_list
            ],
            'value': engine.read_field_value(requisition, field),
        }
        for field in stage.amendable_fields.all()
    ]


def trail_for(module_key, requisition):
    """The configured stage chain annotated with who passed each step."""
    return [
        {
            'key': step['stage'].key,
            'name': step['stage'].name,
            'done': step['done'],
            'current': step['current'],
            'at': step['at'].isoformat() if step['at'] else None,
            'by': step['by'].username if step['by'] else None,
        }
        for step in engine.audit_trail(module_key, requisition)
    ]


def can_view_requisition(user, requisition):
    """Same guard ``detail_view`` applies before rendering anything at all."""
    return bool(
        user.is_admin()
        or user.is_approver()
        or requisition.user_id == user.id
    )


# ---------------------------------------------------------------------------
# Transport — fully driven by the configured chain
# ---------------------------------------------------------------------------
def transport_context(user, requisition):
    """Replicates ``transport_requisition.views.detail_view``'s context."""
    stage = engine.get_stage(TRANSPORT_MODULE, requisition.status)
    can_act = bool(
        stage is not None and not stage.is_terminal
        and engine.stage_allows(stage, user)
    )
    context = {
        'can_view': can_view_requisition(user, requisition),
        'can_act': can_act,
        'stage': stage_info(stage),
        'amendable_fields': amendable_fields_for(requisition, stage) if can_act else [],
        'trail': trail_for(TRANSPORT_MODULE, requisition),
    }
    # The assign form needs the pick lists its template version renders.
    if can_act and stage.can_assign:
        context['vehicles'] = [
            {
                'id': v.id,
                'registration_number': v.registration_number,
                'vehicle_type_display': v.get_vehicle_type_display(),
                'make_model': v.make_model,
            }
            for v in Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE)
        ]
        context['drivers'] = [
            {'id': d.id, 'name': d.name, 'cell_number': d.cell_number}
            for d in Driver.objects.all()
        ]
    return context


def transport_approve(user, requisition, data):
    """Advance past whatever stage the requisition is sitting at.

    Mirrors ``transport_requisition.views.approve_view`` including the amend
    pass-through: a stage flagged ``can_amend`` may correct its fields on the
    way through, and those edits are written to the audit log.
    """
    stage = engine.get_stage(TRANSPORT_MODULE, requisition.status)
    if stage is None:
        raise WorkflowError('This requisition is not awaiting approval.')
    if not engine.stage_allows(stage, user):
        raise WorkflowError(
            f'You are not authorised to act at "{stage.name}".', http_status=403)
    if not stage.can_approve:
        raise WorkflowError(f'"{stage.name}" does not allow approval.')

    amend_details = ''
    if stage.can_amend:
        changes, errors = engine.validate_amendment(stage, data.get('changes') or {})
        if errors:
            raise WorkflowError(' '.join(errors.values()))
        changed = engine.apply_changes(TRANSPORT_MODULE, requisition, changes)
        if changed:
            requisition.grants_remarks = (data.get('remarks') or '').strip()
            requisition.grants_amended = True
            amend_details = 'Amended ' + ', '.join(
                f'{key}: {changes[key]}' for key in changed
            )

    _advance(requisition, stage, user, amend_details)
    return requisition


def transport_decline(user, requisition, data):
    """Mirrors ``transport_requisition.views.reject_view``."""
    stage = engine.get_stage(TRANSPORT_MODULE, requisition.status)
    if stage is None or stage.is_terminal:
        raise WorkflowError('This requisition is no longer pending approval.')
    if not engine.stage_allows(stage, user):
        raise WorkflowError(
            f'You are not authorised to act at "{stage.name}".', http_status=403)
    if not stage.can_decline:
        raise WorkflowError(f'"{stage.name}" does not allow declining.')

    reason = (data.get('reason') or '').strip()
    if not reason and stage.require_reason_on_decline:
        raise WorkflowError(
            'Please give a reason so the requester knows what to fix.')

    _stamp_stage(requisition, stage, user)
    requisition.status = TransportRequisition.Status.REJECTED
    requisition.rejection_reason = reason
    requisition.rejected_at = timezone.now()
    requisition.save()

    log_audit('transport', requisition.pk, requisition.request_number,
              'rejected', user, f'{stage.name}: {reason}')
    notify_requester('transport', requisition, TRANSPORT_MODULE, 'rejected')
    return requisition


def transport_assign(user, requisition, data):
    """Mirrors ``transport_requisition.views.assign_driver_view``."""
    stage = engine.get_stage(TRANSPORT_MODULE, requisition.status)
    assign_stage = next(
        (s for s in engine.get_stages(TRANSPORT_MODULE) if s.can_assign), None)

    if stage is None:
        raise WorkflowError('This requisition is not awaiting assignment.')
    if not engine.stage_allows(stage, user):
        raise WorkflowError(
            f'You are not authorised to act at "{stage.name}".', http_status=403)
    if not stage.can_assign or assign_stage is None:
        raise WorkflowError(
            f'"{stage.name}" does not allow assigning a vehicle.')

    vehicle_id = data.get('vehicle_id')
    driver_id = data.get('driver_id')
    if not vehicle_id or not driver_id:
        raise WorkflowError('Choose both a vehicle and a driver.')

    vehicle = Vehicle.objects.filter(pk=vehicle_id).first()
    driver = Driver.objects.filter(pk=driver_id).first()
    if vehicle is None:
        raise WorkflowError('Choose a valid vehicle.')
    if driver is None:
        raise WorkflowError('Choose a valid driver.')

    requisition.vehicle = vehicle
    requisition.driver = driver
    requisition.assigned_by = user
    requisition.assigned_at = timezone.now()
    requisition.save()

    # Move on to the terminal 'assigned' stage so the requester's tracking page
    # shows the trip as confirmed rather than still in progress.
    following = engine.next_stage(TRANSPORT_MODULE, stage.key)
    requisition.status = (
        following.key if following else TransportRequisition.Status.ASSIGNED)
    requisition.save()

    log_audit('transport', requisition.pk, requisition.request_number,
              'assigned', user,
              f'{requisition.vehicle.registration_number} / {requisition.driver.name}')
    notify_requester('transport', requisition, TRANSPORT_MODULE, 'driver_assigned')
    return requisition


# ---------------------------------------------------------------------------
# ICT / Internal — the fixed two-stage chain (not config driven)
# ---------------------------------------------------------------------------
def two_stage_context(user, requisition, module_key):
    """Shared detail-page context for the two fixed-chain modules.

    ``detail.html`` for these two modules renders first/second approver stamps
    straight off the requisition (the React pages already do the same), so the
    only extra fact the UI needs is whether this user may act right now.
    """
    is_pending = requisition.status in ('pending_first', 'pending_second')
    return {
        'can_view': can_view_requisition(user, requisition),
        'can_act': bool(is_pending and (user.is_approver() or user.is_admin())),
        'module': module_key,
    }


def two_stage_approve(user, requisition, module_key):
    """Mirrors ``*_requisition.views.approve_view`` for ICT and Internal.

    The chain is fixed: ``pending_first`` -> ``pending_second`` -> ``approved``,
    each hop gated by the role that owns it, each hop stamped with who signed.
    """
    if not (user.is_approver() or user.is_admin()):
        raise WorkflowError('You are not authorised to approve requisitions.',
                            http_status=403)

    if requisition.status == 'pending_first':
        if not user.is_first_approver():
            raise WorkflowError(
                'Only a first approver can act on this requisition.',
                http_status=403)
        requisition.status = 'pending_second'
        requisition.first_approver = user
        requisition.first_approved_at = timezone.now()
    elif requisition.status == 'pending_second':
        if not user.is_second_approver():
            raise WorkflowError(
                'Only a second approver can act on this requisition.',
                http_status=403)
        requisition.status = 'approved'
        requisition.second_approver = user
        requisition.second_approved_at = timezone.now()
    else:
        raise WorkflowError('This requisition is not awaiting approval.')

    requisition.save()

    if requisition.status == 'pending_second':
        log_audit(module_key, requisition.pk, requisition.request_number,
                  'pending_second', user)
        send_approval_request(module_key, requisition, module_key, 'pending_second')
        notify_requester(module_key, requisition, module_key, 'pending_second')
    elif requisition.status == 'approved':
        log_audit(module_key, requisition.pk, requisition.request_number,
                  'approved', user)
        notify_requester(module_key, requisition, module_key, 'approved')

    return requisition


def two_stage_decline(user, requisition, module_key, data):
    """Mirrors ``*_requisition.views.reject_view`` for ICT and Internal."""
    if not (user.is_approver() or user.is_admin()):
        raise WorkflowError('You are not authorised to reject requisitions.',
                            http_status=403)
    if requisition.status not in ('pending_first', 'pending_second'):
        raise WorkflowError('This requisition is not awaiting approval.')

    reason = (data.get('reason') or '').strip()

    requisition.status = 'rejected'
    requisition.rejection_reason = reason
    requisition.rejected_at = timezone.now()
    requisition.save()

    log_audit(module_key, requisition.pk, requisition.request_number,
              'rejected', user, reason)
    notify_requester(module_key, requisition, module_key, 'rejected')
    return requisition


# ---------------------------------------------------------------------------
# MeetSpace — booking decisions (no workflow chain, HR admin owns them)
# ---------------------------------------------------------------------------
def booking_context(user, booking):
    """What the MeetSpace detail page needs to pick its buttons.

    Reproduces the ``{% if %}`` guards in ``meetspace/booking_detail.html``:
    HR admins act on pending bookings, the owner answers alternatives, and
    either may cancel while the booking is still live.
    """
    is_owner = booking.user_id == user.id
    hr_admin = _is_hr_admin(user)
    status = booking.status
    live = status in ('approved', 'pending', 'alternatives')
    return {
        'can_view': is_owner or hr_admin,
        'is_owner': is_owner,
        'is_hr_admin': hr_admin,
        'can_approve': status == 'pending' and hr_admin,
        'can_decline': status == 'pending' and hr_admin,
        'can_suggest_alternatives': status == 'pending' and hr_admin,
        'can_cancel': live and (hr_admin or is_owner),
        'can_review_alternatives': status == 'alternatives' and is_owner,
    }


def _is_hr_admin(user):
    """MeetSpace's HR-Admin role, which owns room and booking administration."""
    return user.is_admin() or user.is_hr_admin()


def booking_approve(user, booking):
    """Mirrors ``meetspace.views.booking_approve``."""
    if not _is_hr_admin(user):
        raise WorkflowError('Only HR admins can approve bookings.',
                            http_status=403)
    if booking.status != 'pending':
        raise WorkflowError('Only pending bookings can be approved.')

    booking.status = 'approved'
    booking.save()

    from meetspace.views import _notify
    _notify(
        'Room Booking Approved - MeetSpace',
        f"Hello {booking.user.get_full_name()},\n\nYour meeting room booking has been approved!\n\n"
        f"Meeting: {booking.meeting_title}\nRoom: {booking.room.room_number} ({booking.room.floor})\n"
        f"Date: {booking.date}\nTime: {booking.start_time} - {booking.end_time}\n"
        f"Participants: {booking.number_of_participants}.",
        [booking.user.email],
    )
    return booking


def booking_decline(user, booking, data):
    """Mirrors ``meetspace.views.booking_reject``."""
    if not _is_hr_admin(user):
        raise WorkflowError('Only HR admins can reject bookings.',
                            http_status=403)
    if booking.status != 'pending':
        raise WorkflowError('Only pending bookings can be rejected.')

    reason = (data.get('reason') or '').strip()
    if not reason:
        raise WorkflowError('A rejection reason is required.')

    booking.status = 'rejected'
    booking.cancellation_reason = reason
    booking.cancelled_at = timezone.now()
    booking.cancelled_by = user
    booking.save()

    from meetspace.views import _notify
    _notify(
        'Room Booking Rejected - MeetSpace',
        f"Hello {booking.user.get_full_name()},\n\nYour booking request has been rejected.\n\n"
        f"Meeting: {booking.meeting_title}\nRoom: {booking.room.room_number}\n"
        f"Date: {booking.date}\nTime: {booking.start_time} - {booking.end_time}\n\n"
        f"Reason: {reason}.",
        [booking.user.email],
    )
    return booking


def booking_cancel(user, booking, data):
    """Mirrors ``meetspace.views.booking_cancel``."""
    if not _is_hr_admin(user) and booking.user_id != user.id:
        raise WorkflowError('You do not have permission to cancel this booking.',
                            http_status=403)
    if booking.status not in ('approved', 'pending', 'alternatives'):
        raise WorkflowError('This booking cannot be cancelled.')

    reason = (data.get('reason') or '').strip()
    if not reason:
        raise WorkflowError('A cancellation reason is required.')

    booking.status = 'cancelled'
    booking.cancellation_reason = reason
    booking.cancelled_at = timezone.now()
    booking.cancelled_by = user
    booking.save()
    return booking


def booking_suggest_alternatives(user, booking, data):
    """Mirrors ``meetspace.views.booking_suggest_alternatives``."""
    if not _is_hr_admin(user):
        raise WorkflowError('Only HR admins can suggest alternatives.',
                            http_status=403)
    if booking.status != 'pending':
        raise WorkflowError('Only pending bookings can have alternatives.')

    # Each alternative is a room + date + time range the requester can pick.
    alternatives = []
    for entry in (data.get('alternatives') or []):
        room_id = entry.get('room_id')
        alt_date = entry.get('date')
        start = entry.get('start_time')
        end = entry.get('end_time')
        if room_id and alt_date and start and end:
            alternatives.append({
                'room_id': int(room_id),
                'date': alt_date,
                'start_time': start,
                'end_time': end,
            })

    if not alternatives:
        raise WorkflowError('Add at least one alternative slot.')

    booking.status = 'alternatives'
    booking.alternatives = alternatives
    booking.save()

    lines = '\n'.join(
        f"  Option {i}: Room {a['room_id']} on {a['date']} "
        f"at {a['start_time']}-{a['end_time']}"
        for i, a in enumerate(alternatives, start=1)
    )
    from meetspace.views import _notify
    _notify(
        'Alternative Booking Options - MeetSpace',
        f"Hello {booking.user.get_full_name()},\n\nYour booking request for "
        f"{booking.meeting_title} on {booking.date} at "
        f"{booking.start_time}-{booking.end_time} could not be accommodated.\n\n"
        f"Here are the alternative options:\n{lines}\n\n"
        f"Log in to MeetSpace to accept one of these options.",
        [booking.user.email],
    )
    return booking


def booking_accept_alternative(user, booking, data):
    """Mirrors ``meetspace.views.booking_accept_alternative``."""
    if booking.user_id != user.id:
        raise WorkflowError('You can only respond to alternatives on your own bookings.',
                            http_status=403)
    if booking.status != 'alternatives':
        raise WorkflowError('This booking has no alternatives to respond to.')

    try:
        index = int(data.get('alternative_index'))
        selected = booking.alternatives[index]
    except (TypeError, ValueError, IndexError):
        raise WorkflowError('Choose a valid alternative.')

    from meetspace.models import Room
    booking.date = selected.get('date', booking.date)
    booking.start_time = selected.get('start_time', booking.start_time)
    booking.end_time = selected.get('end_time', booking.end_time)
    room_id = selected.get('room_id')
    if room_id:
        room = Room.objects.filter(pk=room_id).first()
        if room is None:
            raise WorkflowError('Choose a valid alternative.')
        booking.room = room
    booking.status = 'approved'
    booking.alternatives = []
    booking.save()
    return booking


def booking_reject_alternatives(user, booking):
    """Mirrors ``meetspace.views.booking_reject_alternatives``."""
    if booking.user_id != user.id:
        raise WorkflowError('You can only respond to alternatives on your own bookings.',
                            http_status=403)
    if booking.status != 'alternatives':
        raise WorkflowError('This booking has no alternatives to respond to.')

    booking.status = 'rejected'
    booking.cancellation_reason = 'You declined every alternative offered.'
    booking.cancelled_at = timezone.now()
    booking.cancelled_by = user
    booking.alternatives = []
    booking.save()
    return booking
