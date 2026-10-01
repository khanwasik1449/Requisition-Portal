"""MeetSpace views — the room-booking module ported from MeetSpace.

MeetSpace exposed these as a DRF + JWT API. The portal is session-based and
server-rendered, so each endpoint here is a ``@login_required`` view that
renders a template. The business rules are unchanged: who may act, the status
transitions, the conflict check, and the email notifications.
"""

from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from portal_config import engine

from .models import Announcement, Booking, Room

MODULE = 'meetspace'


def _is_hr_admin(user):
    """MeetSpace's HR-Admin role, which owns room and booking administration."""
    return user.is_admin() or user.is_hr_admin()


def _notify(subject, body, recipients):
    """Best-effort email; a mail failure must never roll back a decision."""
    if not recipients:
        return
    try:
        send_mail(subject=subject, message=body, recipient_list=recipients,
                  fail_silently=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@login_required
def dashboard(request):
    """Role-aware overview: admins see everything, employees see their own."""
    today = date.today()
    bookings = Booking.objects.select_related('room', 'user')

    if _is_hr_admin(request.user):
        recent = bookings.order_by('-created_at')[:10]
        stats = {
            'total_rooms': Room.objects.filter(is_active=True).count(),
            'bookings_today': bookings.filter(date=today).count(),
            'upcoming': bookings.filter(date__gte=today).exclude(
                status__in=[Booking.Status.CANCELLED, Booking.Status.REJECTED],
            ).count(),
            'pending': bookings.filter(status=Booking.Status.PENDING).count(),
        }
    else:
        mine = bookings.filter(user=request.user)
        recent = mine.order_by('-created_at')[:10]
        stats = {
            'upcoming': mine.filter(date__gte=today).exclude(
                status__in=[Booking.Status.CANCELLED, Booking.Status.REJECTED],
            ).count(),
            'pending': mine.filter(status=Booking.Status.PENDING).count(),
            'past': mine.filter(date__lt=today).count(),
        }

    announcements = Announcement.objects.select_related('created_by')[:10]
    return render(request, 'meetspace/dashboard.html', {
        'stats': stats,
        'recent': recent,
        'announcements': announcements,
        'is_hr_admin': _is_hr_admin(request.user),
    })


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------
@login_required
def room_list(request):
    rooms = Room.objects.annotate(
        booking_count=models.Count('bookings', filter=Q(bookings__status=Booking.Status.APPROVED)),
    )
    return render(request, 'meetspace/room_list.html', {
        'rooms': rooms,
        'is_hr_admin': _is_hr_admin(request.user),
    })


@login_required
def room_create(request):
    if not _is_hr_admin(request.user):
        messages.error(request, 'Only HR admins can add rooms.')
        return redirect('meetspace:room_list')

    if request.method == 'POST':
        number = (request.POST.get('room_number') or '').strip()
        floor = (request.POST.get('floor') or '').strip()
        try:
            min_occ = int(request.POST.get('min_occupancy') or 1)
            max_occ = int(request.POST.get('max_occupancy') or 10)
        except ValueError:
            messages.error(request, 'Occupancy must be a whole number.')
            return redirect('meetspace:room_create')

        if not number or not floor:
            messages.error(request, 'Room number and floor are required.')
            return redirect('meetspace:room_create')
        if min_occ < 1 or max_occ < min_occ:
            messages.error(request, 'Maximum occupancy must be at least the minimum.')
            return redirect('meetspace:room_create')
        if Room.objects.filter(room_number__iexact=number).exists():
            messages.error(request, f'Room {number} already exists.')
            return redirect('meetspace:room_create')

        Room.objects.create(room_number=number, floor=floor,
                            min_occupancy=min_occ, max_occupancy=max_occ)
        messages.success(request, f'Room {number} added.')
        return redirect('meetspace:room_list')

    return render(request, 'meetspace/room_form.html', {'room': None})


@login_required
def room_edit(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if not _is_hr_admin(request.user):
        messages.error(request, 'Only HR admins can edit rooms.')
        return redirect('meetspace:room_list')

    if request.method == 'POST':
        number = (request.POST.get('room_number') or '').strip()
        floor = (request.POST.get('floor') or '').strip()
        try:
            min_occ = int(request.POST.get('min_occupancy') or 1)
            max_occ = int(request.POST.get('max_occupancy') or 10)
        except ValueError:
            messages.error(request, 'Occupancy must be a whole number.')
            return redirect('meetspace:room_edit', pk=room.pk)

        if not number or not floor:
            messages.error(request, 'Room number and floor are required.')
            return redirect('meetspace:room_edit', pk=room.pk)
        if min_occ < 1 or max_occ < min_occ:
            messages.error(request, 'Maximum occupancy must be at least the minimum.')
            return redirect('meetspace:room_edit', pk=room.pk)
        if Room.objects.filter(room_number__iexact=number).exclude(pk=room.pk).exists():
            messages.error(request, f'Room {number} already exists.')
            return redirect('meetspace:room_edit', pk=room.pk)

        room.room_number = number
        room.floor = floor
        room.min_occupancy = min_occ
        room.max_occupancy = max_occ
        room.save()
        messages.success(request, f'Room {number} updated.')
        return redirect('meetspace:room_list')

    return render(request, 'meetspace/room_form.html', {'room': room})


@login_required
def room_toggle(request, pk):
    """Retire or restore a room without deleting its booking history."""
    room = get_object_or_404(Room, pk=pk)
    if not _is_hr_admin(request.user):
        messages.error(request, 'Only HR admins can change room availability.')
        return redirect('meetspace:room_list')

    room.is_active = not room.is_active
    room.save()
    state = 'available' if room.is_active else 'retired'
    messages.success(request, f'Room {room.room_number} is now {state}.')
    return redirect('meetspace:room_list')


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------
@login_required
def booking_list(request):
    bookings = Booking.objects.select_related('room', 'user')
    if not _is_hr_admin(request.user):
        bookings = bookings.filter(user=request.user)

    status = request.GET.get('status')
    if status:
        bookings = bookings.filter(status=status)

    return render(request, 'meetspace/booking_list.html', {
        'bookings': bookings,
        'is_hr_admin': _is_hr_admin(request.user),
        'status_choices': Booking.Status.choices,
        'current_status': status,
    })


def booking_create(request):
    """Public booking form — no login required, like transport requisitions.

    The requester's email is collected so they can track the booking and
    receive notifications. ``user`` is left null for anonymous submissions.
    """
    rooms = Room.objects.filter(is_active=True)

    if request.method == 'POST':
        title = (request.POST.get('meeting_title') or '').strip()
        room_id = request.POST.get('room')
        date_str = request.POST.get('date')
        start_str = request.POST.get('start_time')
        end_str = request.POST.get('end_time')
        participants = request.POST.get('number_of_participants')
        requirements = (request.POST.get('requirements') or '').strip()
        email = (request.POST.get('email_address') or '').strip()

        errors = []
        if not title:
            errors.append('Meeting title is required.')
        if not email:
            errors.append('Email address is required.')
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append('Enter a valid email address.')

        room = Room.objects.filter(pk=room_id, is_active=True).first() if room_id else None
        if room is None:
            errors.append('Choose an available room.')

        try:
            participants = int(participants)
        except (TypeError, ValueError):
            participants = 0
        if participants < 1:
            errors.append('Number of participants must be at least 1.')

        try:
            booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start = datetime.strptime(start_str, '%H:%M').time()
            end = datetime.strptime(end_str, '%H:%M').time()
        except (TypeError, ValueError):
            errors.append('Enter a valid date and time range.')
            booking_date = start = end = None

        if booking_date and booking_date < date.today():
            errors.append('The booking date cannot be in the past.')
        if start and end and end <= start:
            errors.append('End time must be after start time.')

        if room and participants:
            if participants < room.min_occupancy or participants > room.max_occupancy:
                errors.append(
                    f'Room {room.room_number} supports {room.min_occupancy}–{room.max_occupancy} participants.'
                )

        if not errors and room and booking_date and start and end:
            conflict = Booking.objects.filter(
                room=room, date=booking_date, status=Booking.Status.APPROVED,
            ).filter(Q(start_time__lt=end) & Q(end_time__gt=start)).exists()
            if conflict:
                errors.append('This room is already booked for the selected time slot.')

        if errors:
            for message in errors:
                messages.error(request, message)
            return render(request, 'meetspace/booking_form.html', {
                'rooms': rooms, 'booking': None,
                'posted': request.POST, 'errors': errors,
            }, status=400)

        booking = Booking.objects.create(
            meeting_title=title, date=booking_date, start_time=start, end_time=end,
            number_of_participants=participants, requirements=requirements,
            room=room, user=request.user if request.user.is_authenticated else None,
            email_address=email, status=Booking.Status.PENDING,
        )
        _notify(
            'New Booking Request — MeetSpace',
            f"New booking request from {email}.\n"
            f"Meeting: {booking.meeting_title}\nRoom: {booking.room.room_number}\n"
            f"Date: {booking.date}\nTime: {booking.start_time}–{booking.end_time}.",
            list(_hr_admin_emails()),
        )
        messages.success(request, 'Booking requested. The HR admin has been notified.')
        return render(request, 'meetspace/booking_submitted.html', {'b': booking})

    return render(request, 'meetspace/booking_form.html', {'rooms': rooms, 'booking': None})


def track_view(request):
    """Public self-service status lookup by email address.

    Returns only bookings whose email_address matches exactly
    (case-insensitive), so this cannot be used to enumerate other people's
    bookings.
    """
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        if not email:
            messages.error(request, 'Please enter the email address you used.')
            return render(request, 'meetspace/track.html', {'searched': False}, status=400)
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Enter a valid email address.')
            return render(request, 'meetspace/track.html', {'searched': False}, status=400)

        return render(request, 'meetspace/track.html', {
            'searched': True,
            'email': email,
            'bookings': Booking.objects.filter(email_address__iexact=email),
        })

    return render(request, 'meetspace/track.html', {'searched': False})


@login_required
def booking_detail(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related('room', 'user', 'cancelled_by'), pk=pk,
    )
    if not _is_hr_admin(request.user) and booking.user != request.user:
        return redirect('meetspace:booking_list')

    stage = engine.get_stage(MODULE, booking.status)
    return render(request, 'meetspace/booking_detail.html', {
        'b': booking,
        'stage': stage,
        'is_hr_admin': _is_hr_admin(request.user),
        'can_act': stage is not None and not stage.is_terminal
        and engine.stage_allows(stage, request.user),
        'rooms': Room.objects.filter(is_active=True),
    })


# ---------------------------------------------------------------------------
# Booking decisions
# ---------------------------------------------------------------------------
def _hr_admin_emails():
    from accounts.models import User
    return User.objects.filter(is_active=True, role='hr_admin').values_list('email', flat=True)


@login_required
def booking_approve(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if not _is_hr_admin(request.user):
        messages.error(request, 'Only HR admins can approve bookings.')
        return redirect('meetspace:booking_detail', pk=pk)
    if booking.status != Booking.Status.PENDING:
        messages.error(request, 'Only pending bookings can be approved.')
        return redirect('meetspace:booking_detail', pk=pk)

    booking.status = Booking.Status.APPROVED
    booking.save()
    _notify(
        'Room Booking Approved — MeetSpace',
        f"Hello {booking.user.get_full_name()},\n\nYour meeting room booking has been approved!\n\n"
        f"Meeting: {booking.meeting_title}\nRoom: {booking.room.room_number} ({booking.room.floor})\n"
        f"Date: {booking.date}\nTime: {booking.start_time} – {booking.end_time}\n"
        f"Participants: {booking.number_of_participants}.",
        [booking.user.email],
    )
    messages.success(request, 'Booking approved. Confirmation email sent.')
    return redirect('meetspace:booking_detail', pk=pk)


@login_required
def booking_reject(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if not _is_hr_admin(request.user):
        messages.error(request, 'Only HR admins can reject bookings.')
        return redirect('meetspace:booking_detail', pk=pk)
    if booking.status != Booking.Status.PENDING:
        messages.error(request, 'Only pending bookings can be rejected.')
        return redirect('meetspace:booking_detail', pk=pk)

    if request.method == 'POST':
        reason = (request.POST.get('reason') or '').strip()
        if not reason:
            messages.error(request, 'A rejection reason is required.')
            return redirect('meetspace:booking_reject', pk=pk)

        booking.status = Booking.Status.REJECTED
        booking.cancellation_reason = reason
        booking.cancelled_at = timezone.now()
        booking.cancelled_by = request.user
        booking.save()
        _notify(
            'Room Booking Rejected — MeetSpace',
            f"Hello {booking.user.get_full_name()},\n\nYour booking request has been rejected.\n\n"
            f"Meeting: {booking.meeting_title}\nRoom: {booking.room.room_number}\n"
            f"Date: {booking.date}\nTime: {booking.start_time} – {booking.end_time}\n\n"
            f"Reason: {reason}.",
            [booking.user.email],
        )
        messages.success(request, 'Booking rejected. Notification email sent.')
        return redirect('meetspace:booking_detail', pk=pk)

    return render(request, 'meetspace/reject_reason.html', {'b': booking})


@login_required
def booking_suggest_alternatives(request, pk):
    """Offer the requester different rooms/times instead of a flat rejection."""
    booking = get_object_or_404(Booking, pk=pk)
    if not _is_hr_admin(request.user):
        messages.error(request, 'Only HR admins can suggest alternatives.')
        return redirect('meetspace:booking_detail', pk=pk)
    if booking.status != Booking.Status.PENDING:
        messages.error(request, 'Only pending bookings can have alternatives.')
        return redirect('meetspace:booking_detail', pk=pk)

    if request.method == 'POST':
        # Each alternative is a room + date + time range the requester can pick.
        alternatives = []
        for key in request.POST:
            if key.startswith('alt_room_'):
                index = key.rsplit('_', 1)[-1]
                room_id = request.POST.get(f'alt_room_{index}')
                alt_date = request.POST.get(f'alt_date_{index}')
                start = request.POST.get(f'alt_start_{index}')
                end = request.POST.get(f'alt_end_{index}')
                if room_id and alt_date and start and end:
                    alternatives.append({
                        'room_id': int(room_id),
                        'date': alt_date,
                        'start_time': start,
                        'end_time': end,
                    })

        if not alternatives:
            messages.error(request, 'Add at least one alternative slot.')
            return redirect('meetspace:booking_suggest_alternatives', pk=pk)

        booking.status = Booking.Status.ALTERNATIVES
        booking.alternatives = alternatives
        booking.save()

        lines = '\n'.join(
            f"  Option {i}: Room {a['room_id']} on {a['date']} at {a['start_time']}–{a['end_time']}"
            for i, a in enumerate(alternatives, start=1)
        )
        _notify(
            'Alternative Booking Options — MeetSpace',
            f"Hello {booking.user.get_full_name()},\n\nYour booking request for "
            f"{booking.meeting_title} on {booking.date} at "
            f"{booking.start_time}–{booking.end_time} could not be accommodated.\n\n"
            f"Here are the alternative options:\n{lines}\n\n"
            f"Log in to MeetSpace to accept one of these options.",
            [booking.user.email],
        )
        messages.success(request, 'Alternatives suggested. Email sent to the requester.')
        return redirect('meetspace:booking_detail', pk=pk)

    return render(request, 'meetspace/suggest_alternatives.html', {
        'b': booking,
        'rooms': Room.objects.filter(is_active=True),
    })


@login_required
def booking_accept_alternative(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.user != request.user:
        messages.error(request, 'You can only respond to alternatives on your own bookings.')
        return redirect('meetspace:booking_detail', pk=pk)
    if booking.status != Booking.Status.ALTERNATIVES:
        messages.error(request, 'This booking has no alternatives to respond to.')
        return redirect('meetspace:booking_detail', pk=pk)

    if request.method == 'POST':
        try:
            index = int(request.POST.get('alternative_index'))
            selected = booking.alternatives[index]
        except (TypeError, ValueError, IndexError):
            messages.error(request, 'Choose a valid alternative.')
            return redirect('meetspace:booking_detail', pk=pk)

        booking.date = selected.get('date', booking.date)
        booking.start_time = selected.get('start_time', booking.start_time)
        booking.end_time = selected.get('end_time', booking.end_time)
        room_id = selected.get('room_id')
        if room_id:
            booking.room = get_object_or_404(Room, pk=room_id)
        booking.status = Booking.Status.APPROVED
        booking.alternatives = []
        booking.save()
        messages.success(request, 'Alternative accepted. Your booking is confirmed.')
        return redirect('meetspace:booking_detail', pk=pk)

    return render(request, 'meetspace/accept_alternative.html', {'b': booking})


@login_required
def booking_reject_alternatives(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.user != request.user:
        messages.error(request, 'You can only respond to alternatives on your own bookings.')
        return redirect('meetspace:booking_detail', pk=pk)
    if booking.status != Booking.Status.ALTERNATIVES:
        messages.error(request, 'This booking has no alternatives to respond to.')
        return redirect('meetspace:booking_detail', pk=pk)

    booking.status = Booking.Status.REJECTED
    booking.cancellation_reason = 'You declined every alternative offered.'
    booking.cancelled_at = timezone.now()
    booking.cancelled_by = request.user
    booking.alternatives = []
    booking.save()
    messages.success(request, 'Alternatives declined. The booking has been rejected.')
    return redirect('meetspace:booking_detail', pk=pk)


@login_required
def booking_cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if not _is_hr_admin(request.user) and booking.user != request.user:
        messages.error(request, 'You do not have permission to cancel this booking.')
        return redirect('meetspace:booking_detail', pk=pk)
    if booking.status not in (Booking.Status.APPROVED, Booking.Status.PENDING,
                              Booking.Status.ALTERNATIVES):
        messages.error(request, 'This booking cannot be cancelled.')
        return redirect('meetspace:booking_detail', pk=pk)

    if request.method == 'POST':
        reason = (request.POST.get('reason') or '').strip()
        if not reason:
            messages.error(request, 'A cancellation reason is required.')
            return redirect('meetspace:booking_cancel', pk=pk)

        booking.status = Booking.Status.CANCELLED
        booking.cancellation_reason = reason
        booking.cancelled_at = timezone.now()
        booking.cancelled_by = request.user
        booking.save()
        messages.success(request, 'Booking cancelled.')
        return redirect('meetspace:booking_detail', pk=pk)

    return render(request, 'meetspace/cancel_reason.html', {'b': booking})


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------
@login_required
def availability(request):
    """Find free rooms for a slot, suggesting nearby times when none match."""
    results = None
    suggestions = []
    searched = False

    if request.method == 'POST':
        searched = True
        try:
            search_date = datetime.strptime(request.POST.get('date', ''), '%Y-%m-%d').date()
            start = datetime.strptime(request.POST.get('start_time', ''), '%H:%M').time()
            end = datetime.strptime(request.POST.get('end_time', ''), '%H:%M').time()
            participants = int(request.POST.get('number_of_participants') or 0)
        except (TypeError, ValueError):
            messages.error(request, 'Enter a valid date, time range and participant count.')
            return redirect('meetspace:availability')

        suitable = Room.objects.filter(
            is_active=True, min_occupancy__lte=participants, max_occupancy__gte=participants,
        )
        taken = Booking.objects.filter(
            date=search_date, status=Booking.Status.APPROVED,
        ).filter(Q(start_time__lt=end) & Q(end_time__gt=start)).values_list('room_id', flat=True)
        results = suitable.exclude(id__in=taken)

        if not results.exists():
            suggestions = _time_suggestions(search_date, start, end, participants)

    return render(request, 'meetspace/availability.html', {
        'results': results,
        'suggestions': suggestions,
        'searched': searched,
    })


def _time_suggestions(search_date, start_time, end_time, participants, limit=10):
    """Scan the next three days in 30-minute steps for a free matching slot."""
    suitable = Room.objects.filter(
        is_active=True, min_occupancy__lte=participants, max_occupancy__gte=participants,
    )
    duration = datetime.combine(search_date, end_time) - datetime.combine(search_date, start_time)
    found = []

    for day_offset in range(3):
        day = search_date + timedelta(days=day_offset)
        for minutes in range(0, 12 * 60 + 1, 30):
            new_start = datetime.combine(day, datetime.min.time()) + timedelta(hours=8, minutes=minutes)
            new_end = new_start + duration
            if new_end.hour >= 20:
                break
            if day_offset == 0 and new_start.time() <= start_time:
                continue
            for room in suitable:
                clash = Booking.objects.filter(
                    room=room, date=day, status=Booking.Status.APPROVED,
                ).filter(Q(start_time__lt=new_end.time()) & Q(end_time__gt=new_start.time()))
                if not clash.exists():
                    found.append({'room': room, 'date': day,
                                  'start_time': new_start.time(), 'end_time': new_end.time()})
                    if len(found) >= limit:
                        return found
    return found


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------
@login_required
def announcement_create(request):
    if not _is_hr_admin(request.user):
        messages.error(request, 'Only HR admins can post announcements.')
        return redirect('meetspace:dashboard')

    if request.method == 'POST':
        message_text = (request.POST.get('message') or '').strip()
        attachment = request.FILES.get('attachment')
        if not message_text and not attachment:
            messages.error(request, 'Provide announcement text, an attachment, or both.')
            return redirect('meetspace:announcement_create')

        Announcement.objects.create(
            message=message_text, attachment=attachment or None, created_by=request.user,
        )
        messages.success(request, 'Announcement posted.')
        return redirect('meetspace:dashboard')

    return render(request, 'meetspace/announcement_form.html')


@login_required
def announcement_delete(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if not _is_hr_admin(request.user):
        messages.error(request, 'Only HR admins can delete announcements.')
        return redirect('meetspace:dashboard')
    announcement.delete()
    messages.success(request, 'Announcement removed.')
    return redirect('meetspace:dashboard')
