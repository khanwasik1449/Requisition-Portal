from django.conf import settings
from django.db import models


class Room(models.Model):
    """A bookable meeting room.

    Deleting a room would destroy booking history, so removal is done by
    clearing ``is_active`` -- the room stops appearing in search and can no
    longer be booked, but past bookings keep their record of where they were.
    """

    room_number = models.CharField(max_length=20, unique=True)
    floor = models.CharField(max_length=50)
    min_occupancy = models.PositiveIntegerField(default=1)
    max_occupancy = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['room_number']

    def __str__(self):
        return f"Room {self.room_number} (Floor {self.floor})"


class Booking(models.Model):
    """A meeting-room request.

    Ported from MeetSpace, where this was a DRF resource. The lifecycle is
    ``pending`` -> ``approved`` / ``rejected`` / ``cancelled``, with a detour
    through ``alternatives`` when the HR admin offers different slots.

    ``status`` doubles as the workflow stage key, so the approval chain is
    editable from the Form Builder like every other module's.

    Like transport requisitions, bookings can be submitted without an account:
    ``user`` is null for public submissions and ``email_address`` is what the
    requester uses to track the booking and receive notifications.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
        ALTERNATIVES = 'alternatives', 'Alternatives offered'

    meeting_title = models.CharField(max_length=300)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    number_of_participants = models.PositiveIntegerField()
    requirements = models.TextField(blank=True)

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='bookings')
    # Null when booked from the public form (no login). SET_NULL so deleting a
    # user account never destroys a public booking.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='meetspace_bookings',
    )
    # Always required — the public form collects it and it drives tracking.
    email_address = models.EmailField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='meetspace_cancelled_bookings',
    )
    # Free-form list of {room_id, date, start_time, end_time} options the HR
    # admin offered instead of the requested slot.
    alternatives = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.meeting_title} — {self.room.room_number} ({self.date} {self.start_time}-{self.end_time})"

    @property
    def is_upcoming(self):
        from datetime import date
        return self.date >= date.today()


class Announcement(models.Model):
    """A notice shown on the MeetSpace dashboard.

    Either text or an attachment is required; both may be given.
    """

    message = models.TextField()
    attachment = models.FileField(upload_to='announcements/', blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meetspace_announcements',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Announcement #{self.pk} by {self.created_by}"
