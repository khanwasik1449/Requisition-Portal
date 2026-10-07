from datetime import date, datetime
import decimal

from django.db.models import Q
from rest_framework import serializers
from accounts.models import User
from transport_requisition.models import TransportRequisition, Vehicle, Driver
from meetspace.models import Booking, Room, Announcement
from ict_requisition.models import ICTRequisition
from internal_requisition.models import InternalRequisition
from contracts.models import (
    Contract,
    EmailConfig as ContractEmailConfig,
    EmailLog as ContractEmailLog,
)
from employees.models import Employee
from payslip.models import Payslip, PayslipRequest
from portal_config.models import Module, FormField, WorkflowStage
# NB: `contracts` has its own EmailConfig/EmailLog for contract notices. The
# sidebar's "Email Settings" and "Email Logs" pages read the *notifications*
# ones, so those are what `email-configs` / `email-logs` must serialize.
from notifications.models import (
    AuditLog, EmailConfig, EmailLog,
    EmailLog as NotificationEmailLog,
)


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_display', 'phone',
            'is_active', 'is_staff', 'date_joined', 'last_login',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'is_staff']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    # accounts/user_form.html has no confirmation box -- it only ever asks once.
    # Optional (rather than dropped) so the registration flow, which does ask
    # twice, keeps validating the pair it sends.
    password_confirm = serializers.CharField(write_only=True, required=False)
    # The form's "Active (can log in)" tick defaults to on for a new user and
    # is submitted with every create, which this serializer did not accept.
    is_active = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = User
        # `id` mirrors what every other create in this API returns, so the
        # caller can address the row it just made.
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'password',
            'password_confirm', 'role', 'phone', 'is_active',
        ]

    def validate(self, attrs):
        confirm = attrs.get('password_confirm')
        if confirm is not None and confirm != attrs['password']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    # user_form.html lets an admin reset a password from the edit screen
    # ("Leave blank to keep current"), which nothing here supported before.
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True,
        help_text='Leave blank to keep the current password.')

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'role', 'phone', 'is_active',
            'password',
        ]

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=['password'])
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        return attrs


# Transport Requisition Serializers
class VehicleSerializer(serializers.ModelSerializer):
    # main's transport detail template prints ``vehicle.get_vehicle_type_display``
    # next to the registration, so expose the label as well as the raw choice.
    vehicle_type_display = serializers.CharField(
        source='get_vehicle_type_display', read_only=True)

    class Meta:
        model = Vehicle
        fields = '__all__'


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = '__all__'


class TransportRequisitionListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    vehicle_name = serializers.CharField(source='vehicle.registration_number', read_only=True)
    driver_name = serializers.CharField(source='driver.name', read_only=True)

    class Meta:
        model = TransportRequisition
        fields = [
            'id', 'request_number', 'user', 'user_name', 'user_email', 'full_name',
            'destination', 'travelling_reason', 'pick_up_date', 'pick_up_time',
            'drop_off_date', 'drop_off_time', 'num_passengers', 'status',
            'status_display', 'vehicle', 'vehicle_name', 'driver', 'driver_name',
            'created_at', 'updated_at',
        ]


class TransportTrackSerializer(serializers.ModelSerializer):
    """Self-service status view of one requisition.

    Mirrors what ``templates/transport_requisition/track.html`` renders for an
    exact email match, including the assigned driver's contact details.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    vehicle_type_display = serializers.CharField(source='get_vehicle_type_display', read_only=True)

    # The driver is nullable until transport assigns one, so read through it
    # explicitly rather than relying on a dotted `source`.
    driver_name = serializers.SerializerMethodField()
    driver_car_no = serializers.SerializerMethodField()
    driver_cell_number = serializers.SerializerMethodField()

    class Meta:
        model = TransportRequisition
        fields = [
            'id', 'request_number', 'status', 'status_display',
            'destination', 'pick_up_date', 'pick_up_time', 'pick_up_location',
            'drop_off_date', 'drop_off_time', 'drop_off_location',
            'vehicle_type', 'vehicle_type_display', 'num_passengers',
            'rejection_reason', 'driver_name', 'driver_car_no', 'driver_cell_number',
            'created_at',
        ]

    def get_driver_name(self, obj):
        return obj.driver.name if obj.driver else ''

    def get_driver_car_no(self, obj):
        return obj.driver.car_no if obj.driver else ''

    def get_driver_cell_number(self, obj):
        return obj.driver.cell_number if obj.driver else ''


class TransportHistorySerializer(serializers.ModelSerializer):
    """Everything the admin Tracking History page renders for one request.

    Deliberately wider than the list serializer: the template shows contact
    details, PIN and the full pick-up/drop-off pair, then the audit trail.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # Submitted through the public form, so `user` is NULL -- never use a
    # dotted source on it.
    is_public = serializers.SerializerMethodField()
    driver_name = serializers.SerializerMethodField()
    trail = serializers.SerializerMethodField()

    class Meta:
        model = TransportRequisition
        fields = [
            'id', 'request_number', 'full_name', 'email_address', 'mobile_number',
            'designation', 'pin', 'destination', 'num_passengers',
            'pick_up_date', 'pick_up_time', 'drop_off_date', 'drop_off_time',
            'travelling_reason', 'status', 'status_display', 'is_public',
            'driver_name', 'trail',
        ]

    def get_is_public(self, obj):
        return obj.user_id is None

    def get_driver_name(self, obj):
        return obj.driver.name if obj.driver_id else ''

    def get_trail(self, obj):
        # Attached by the view in a single bulk query, mirroring `r.trail`.
        trail = getattr(obj, 'trail', None)
        if trail is None:
            return []
        return AuditLogSerializer(trail, many=True).data


class TransportReportSerializer(serializers.ModelSerializer):
    """Row shape of the transport report table."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    vehicle_type_display = serializers.CharField(source='get_vehicle_type_display', read_only=True)
    driver_name = serializers.SerializerMethodField()

    class Meta:
        model = TransportRequisition
        fields = [
            'id', 'request_number', 'full_name', 'destination',
            'vehicle_type', 'vehicle_type_display', 'vehicle_type_other',
            'pick_up_date', 'driver_name', 'status', 'status_display',
        ]

    def get_driver_name(self, obj):
        return obj.driver.name if obj.driver_id else ''


class TransportRequisitionDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    driver = DriverSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    extra_data = serializers.JSONField(read_only=True)
    # main's detail template shows "Assigned by <username> on <date>".
    assigned_by = serializers.SlugRelatedField(slug_field='username', read_only=True)

    class Meta:
        model = TransportRequisition
        fields = '__all__'
        read_only_fields = ['id', 'request_number', 'user', 'created_at', 'updated_at', 'extra_data']


class TransportRequisitionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportRequisition
        fields = [
            # Personal information — the model columns are required and the
            # applicant's email is what the public track page searches on, so
            # they must be persisted rather than dropped.
            'full_name', 'email_address', 'mobile_number', 'designation', 'pin',
            'destination', 'travelling_reason', 'pick_up_date', 'pick_up_time',
            'drop_off_date', 'drop_off_time', 'num_passengers', 'vehicle_type',
            'vehicle_type_other', 'pick_up_location', 'drop_off_location',
            'project_name_code', 'budget_code', 'extra_data',
        ]

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TransportRequisitionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportRequisition
        fields = [
            'destination', 'travelling_reason', 'pick_up_date', 'pick_up_time',
            'drop_off_date', 'drop_off_time', 'num_passengers', 'vehicle_type',
            'vehicle_type_other', 'pick_up_location', 'drop_off_location',
            'project_name_code', 'budget_code', 'extra_data',
        ]


class TransportRequisitionActionSerializer(serializers.Serializer):
    """Body shared by every transport stage decision.

    ``action`` is redundant with the URL the request lands on, but it is kept so
    existing callers of ``POST /api/transport/{pk}/approve/`` keep working
    unchanged.
    """
    action = serializers.ChoiceField(
        choices=['approve', 'decline', 'amend', 'assign'], required=False)
    comment = serializers.CharField(required=False, allow_blank=True)
    # Decline reason / approve remarks (``reason`` mirrors the reject form).
    reason = serializers.CharField(required=False, allow_blank=True)
    remarks = serializers.CharField(required=False, allow_blank=True)
    # Amendable field values, keyed by FormField.key (project_name_code, budget_code, ...)
    changes = serializers.DictField(child=serializers.CharField(), required=False)
    # For assign action
    vehicle_id = serializers.IntegerField(required=False, allow_null=True)
    driver_id = serializers.IntegerField(required=False, allow_null=True)


# MeetSpace Serializers
class RoomSerializer(serializers.ModelSerializer):
    # room_list.html prints `room.booking_count`, annotated in
    # RoomViewSet.get_queryset. It is not a model field, so it has to be
    # declared here for `Meta.fields` to carry it through.
    booking_count = serializers.IntegerField(read_only=True, default=0)
    # meetspace.views.room_create/room_edit check the number case-insensitively
    # and report their own sentence, so DRF's case-sensitive UniqueValidator
    # (attached automatically for `unique=True`) is replaced by validate() below.
    room_number = serializers.CharField(max_length=20, allow_blank=True, validators=[])
    floor = serializers.CharField(max_length=50, allow_blank=True)
    # Deliberately plain IntegerField: PositiveIntegerField would reject 0 and
    # negatives with DRF's own wording before this serializer could answer with
    # the message the template shows.
    min_occupancy = serializers.IntegerField()
    max_occupancy = serializers.IntegerField()

    class Meta:
        model = Room
        fields = [
            'id', 'room_number', 'floor', 'min_occupancy', 'max_occupancy',
            'is_active', 'created_at', 'updated_at', 'booking_count',
        ]

    def validate(self, attrs):
        """The checks meetspace.views.room_create / room_edit do by hand.

        main reports these as flash messages rather than field errors, so they
        arrive as ``non_field_errors`` here -- which is where the React form
        shows them.
        """
        instance = self.instance
        number = attrs.get('room_number', instance.room_number if instance else '')
        floor = attrs.get('floor', instance.floor if instance else '')
        min_occ = attrs.get('min_occupancy', instance.min_occupancy if instance else 1)
        max_occ = attrs.get('max_occupancy', instance.max_occupancy if instance else 10)

        if not number or not floor:
            raise serializers.ValidationError('Room number and floor are required.')
        if min_occ < 1 or max_occ < min_occ:
            raise serializers.ValidationError(
                'Maximum occupancy must be at least the minimum.')

        clash = Room.objects.filter(room_number__iexact=number.strip())
        if instance:
            clash = clash.exclude(pk=instance.pk)
        if clash.exists():
            raise serializers.ValidationError(f'Room {number} already exists.')

        attrs['room_number'] = number.strip()
        attrs['floor'] = floor.strip()
        attrs['min_occupancy'] = min_occ
        attrs['max_occupancy'] = max_occ
        return attrs


class BookingListSerializer(serializers.ModelSerializer):
    # booking_list.html renders `b.room.room_number`. `Room` has no `name`, so
    # the earlier `source='room.name'` raised AttributeError on every row and
    # DRF dropped the field (read-only fields are skipped when their attribute
    # is missing) -- which left the React list's Room column permanently blank.
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    room_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # `user` is null for public submissions, where get_full_name() cannot be
    # reached; the template just prints nothing in that case.
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'room', 'room_number', 'room_name', 'user', 'user_name',
            'email_address', 'meeting_title', 'date', 'start_time', 'end_time',
            'status', 'status_display', 'created_at', 'updated_at',
        ]

    def get_room_name(self, obj):
        return str(obj.room) if obj.room_id else ''

    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user_id else ''


class BookingDetailSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # booking_detail.html signs the reason with "by <full name> on <date>".
    cancelled_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_cancelled_by_name(self, obj):
        # Matches {{ b.cancelled_by.get_full_name }}, which falls back to the
        # username when both name fields are blank.
        if not obj.cancelled_by:
            return None
        return obj.cancelled_by.get_full_name() or obj.cancelled_by.username


class BookingCreateSerializer(serializers.ModelSerializer):
    """meetspace.views.booking_create, check for check.

    main validates by hand and flashes *every* message it finds, so validate()
    collects the same sentences in the same order instead of letting DRF stop at
    the first bad field. The React form renders them together, which is what the
    template's `{% for e in errors %}` loop does.

    The date/time fields stay CharFields so a malformed value produces main's
    "Enter a valid date and time range." rather than DRF's format sentence.
    """
    # source='room_id' so the *response* reads the raw id. Without it DRF would
    # resolve instance.room into a Room object and hand it to IntegerField, which
    # dies on int(Room) the moment a booking comes back.
    room = serializers.IntegerField(source='room_id', allow_null=True, required=False)
    meeting_title = serializers.CharField(max_length=300, allow_blank=True)
    email_address = serializers.EmailField(allow_blank=True)
    # IntegerField rather than CharField so the response keeps the numeric type
    # the rest of the app reads; `0` passes the field itself, and validate()
    # below is what turns it into main's "at least 1" sentence.
    number_of_participants = serializers.IntegerField(allow_null=True, required=False)
    requirements = serializers.CharField(allow_blank=True, required=False)
    date = serializers.CharField(allow_blank=True)
    start_time = serializers.CharField(allow_blank=True)
    end_time = serializers.CharField(allow_blank=True)

    class Meta:
        model = Booking
        fields = [
            # `date` was missing here even though booking_form.html collects it
            # and MeetSpaceBooking.tsx posts it -- DRF discards payload keys that
            # are not in `fields`, so every booking INSERT went out without a
            # NOT NULL column and came back 500.
            'id', 'room', 'meeting_title', 'requirements', 'date',
            'start_time', 'end_time',
            'email_address', 'number_of_participants',
        ]
        # AutoField is read-only by default; listed here only so the client can
        # follow the new booking to its detail page.

    def validate(self, attrs):
        errors = []

        title = (attrs.get('meeting_title') or '').strip()
        email = (attrs.get('email_address') or '').strip()
        if not title:
            errors.append('Meeting title is required.')
        if not email:
            # An unparseable address was already answered by EmailField with
            # main's own "Enter a valid email address."
            errors.append('Email address is required.')

        room_id = attrs.get('room_id')
        room = Room.objects.filter(pk=room_id, is_active=True).first() if room_id else None
        if room is None:
            errors.append('Choose an available room.')

        try:
            participants = int(attrs.get('number_of_participants') or 0)
        except (TypeError, ValueError):
            participants = 0
        if participants < 1:
            errors.append('Number of participants must be at least 1.')

        try:
            booking_date = datetime.strptime(attrs.get('date') or '', '%Y-%m-%d').date()
            start = datetime.strptime(attrs.get('start_time') or '', '%H:%M').time()
            end = datetime.strptime(attrs.get('end_time') or '', '%H:%M').time()
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
                    f'Room {room.room_number} supports '
                    f'{room.min_occupancy}–{room.max_occupancy} participants.'
                )

        if not errors and room and booking_date and start and end:
            conflict = Booking.objects.filter(
                room=room, date=booking_date, status=Booking.Status.APPROVED,
            ).filter(Q(start_time__lt=end) & Q(end_time__gt=start)).exists()
            if conflict:
                errors.append('This room is already booked for the selected time slot.')

        if errors:
            raise serializers.ValidationError(errors)

        # `room_id` is left as the plain id: Booking(**attrs) takes it directly,
        # and validate() has already resolved it to an is_active Room above.
        attrs['meeting_title'] = title
        attrs['email_address'] = email
        attrs['date'] = booking_date
        attrs['start_time'] = start
        attrs['end_time'] = end
        attrs['number_of_participants'] = participants
        attrs['requirements'] = (attrs.get('requirements') or '').strip()
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        # main records the address the *applicant* typed so the public track page
        # and the notification reach them, and only tags the row with the
        # signed-in account (or null when anonymous). It never substitutes the
        # account's own address for the one on the form.
        if request is not None and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class BookingActionSerializer(serializers.Serializer):
    """Body shared by the MeetSpace booking decisions."""
    action = serializers.ChoiceField(
        choices=['approve', 'decline', 'suggest_alternative'], required=False)
    comment = serializers.CharField(required=False, allow_blank=True)
    # Rejection / cancellation reason — required by the reject & cancel forms.
    reason = serializers.CharField(required=False, allow_blank=True)
    # For suggest_alternative: one or more room + slot offers the requester picks from.
    alternatives = serializers.ListField(child=serializers.DictField(), required=False)
    # For accept_alternative: index into Booking.alternatives
    alternative_index = serializers.IntegerField(required=False, allow_null=True)


class BookingTrackSerializer(serializers.ModelSerializer):
    """Exactly the rows meetspace/track.html renders.

    Deliberately narrower than BookingDetailSerializer: the lookup is public and
    keyed only on an email address, so the requester record the template never
    shows is not handed back to an anonymous caller.
    """
    room = RoomSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'meeting_title', 'status', 'status_display', 'date',
            'start_time', 'end_time', 'number_of_participants',
            'requirements', 'cancellation_reason', 'room',
        ]


class AnnouncementSerializer(serializers.ModelSerializer):
    # dashboard.html prints `a.created_by.get_full_name`, which a bare
    # `fields = '__all__'` would only give back as a user id.
    created_by_name = serializers.SerializerMethodField()
    # Deferred to validate() so an empty post answers with main's sentence
    # rather than DRF's "This field may not be blank."
    message = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = Announcement
        # `Announcement` has no `updated_at` -- only `created_at`.
        fields = [
            'id', 'message', 'attachment', 'created_by', 'created_by_name',
            'created_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_by_name', 'created_at']

    def get_created_by_name(self, obj):
        if not obj.created_by_id:
            return ''
        return obj.created_by.get_full_name() or obj.created_by.username

    def validate(self, attrs):
        """announcement_create's "text, attachment, or both" rule, verbatim."""
        message = attrs.get('message', self.instance.message if self.instance else '')
        attachment = attrs.get(
            'attachment', self.instance.attachment if self.instance else None)
        if not (message or '').strip() and not attachment:
            raise serializers.ValidationError(
                'Provide announcement text, an attachment, or both.')
        attrs['message'] = (message or '').strip()
        return attrs


# ICT Requisition Serializers
class ICTRequisitionListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ICTRequisition
        fields = [
            'id', 'request_number', 'user', 'user_name', 'device_equipment',
            'status', 'status_display',
            'created_at', 'updated_at',
        ]


class ICTRequisitionDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # detail.html prints "{{ r.first_approver.username }}" — expose the name
    # alongside the raw FK so the React page can render the same line.
    first_approver_name = serializers.SlugRelatedField(
        slug_field='username', source='first_approver', read_only=True)
    second_approver_name = serializers.SlugRelatedField(
        slug_field='username', source='second_approver', read_only=True)

    class Meta:
        model = ICTRequisition
        fields = '__all__'
        read_only_fields = ['id', 'request_number', 'user', 'created_at', 'updated_at']


class ICTRequisitionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ICTRequisition
        fields = ['device_equipment', 'equipment_specification', 'purpose', 'requisition_date', 'requirement_date', 'return_date', 'supervisor']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ICTRequisitionActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'decline'], required=False)
    comment = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)


# Internal Requisition Serializers
class InternalRequisitionListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = InternalRequisition
        fields = [
            'id', 'request_number', 'user', 'user_name', 'department',
            'status', 'status_display',
            'created_at', 'updated_at',
        ]


class InternalRequisitionDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # detail.html prints "{{ r.first_approver.username }}" — expose the name
    # alongside the raw FK so the React page can render the same line.
    first_approver_name = serializers.SlugRelatedField(
        slug_field='username', source='first_approver', read_only=True)
    second_approver_name = serializers.SlugRelatedField(
        slug_field='username', source='second_approver', read_only=True)

    class Meta:
        model = InternalRequisition
        fields = '__all__'
        read_only_fields = ['id', 'request_number', 'user', 'created_at', 'updated_at']


class InternalRequisitionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalRequisition
        fields = ['department', 'full_name', 'email_address', 'mobile_number', 'designation', 'pin']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class InternalRequisitionActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'decline'], required=False)
    comment = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)


# Contracts Serializers
class ContractSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_contract_type_display', read_only=True)

    class Meta:
        model = Contract
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        """contracts/views.create_contract's guard, verbatim.

        Both dates carry a model default, so DRF would let a POST through
        without them -- the template refuses instead. Checked against the
        submitted values only, which is what `request.POST.get(...)` sees.
        """
        if self.instance is not None and self.partial:
            return attrs

        start = attrs.get('start_date')
        end = attrs.get('end_date')
        salary = attrs.get('salary')
        try:
            salary_ok = float(salary or 0) > 0
        except (TypeError, ValueError):
            salary_ok = False

        if not start or not end or not salary_ok:
            raise serializers.ValidationError(
                'Start date, end date, and salary are required.')
        return attrs


class EmailConfigSerializer(serializers.ModelSerializer):
    department_display = serializers.CharField(
        source='get_department_display', read_only=True)

    class Meta:
        model = EmailConfig
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmailLogSerializer(serializers.ModelSerializer):
    department_display = serializers.CharField(source='get_department_display', read_only=True)
    email_type_display = serializers.CharField(source='get_email_type_display', read_only=True)

    class Meta:
        model = EmailLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


# Employees Serializers
class EmployeeSerializer(serializers.ModelSerializer):
    # Contract history is keyed by PIN -- Contract has no FK to Employee, so it
    # cannot be annotated onto the queryset. Computed the same way
    # employees.views.employee_list does it.
    new_count = serializers.SerializerMethodField()
    extension_count = serializers.SerializerMethodField()
    revision_count = serializers.SerializerMethodField()
    renewal_count = serializers.SerializerMethodField()

    # add_employee / edit_employee read every one of these straight off the
    # POST as free text, so the plain-field coercions below reproduce the
    # view's own `or` expressions instead of DRF's stricter defaults:
    #   - `designation` is a non-blank model column, which would make DRF say
    #     "This field may not be blank." before validate() can say what the
    #     template says ("Designation is required.").
    #   - `email` is an EmailField, but the view never checks the format --
    #     only that it is non-empty.
    #   - `salary` arrives as `request.POST.get("salary") or 0`.
    #   - `gender`/`tin`/`phone` arrive as `request.POST.get(...) or None`.
    designation = serializers.CharField(max_length=200, required=False,
                                        allow_blank=True)
    email = serializers.CharField(max_length=254, required=False,
                                  allow_blank=True, allow_null=True)
    salary = serializers.CharField(required=False, allow_blank=True,
                                   allow_null=True)
    gender = serializers.CharField(max_length=20, required=False,
                                   allow_blank=True, allow_null=True)
    tin = serializers.CharField(max_length=50, required=False,
                                allow_blank=True, allow_null=True)
    phone = serializers.CharField(max_length=15, required=False,
                                  allow_blank=True, allow_null=True)

    class Meta:
        model = Employee
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

    def validate_salary(self, value):
        """`request.POST.get("salary") or 0` -- a blank cell is 0, anything
        else has to be a number the model can store."""
        value = (value or '').strip().replace(',', '')
        if not value:
            return decimal.Decimal('0')
        try:
            return decimal.Decimal(value)
        except decimal.InvalidOperation:
            raise serializers.ValidationError('A valid number is required.')

    def _contract_count(self, obj, contract_type):
        return Contract.objects.filter(pin=obj.pin, contract_type=contract_type).count()

    def get_new_count(self, obj):
        return self._contract_count(obj, 'New')

    def get_extension_count(self, obj):
        return self._contract_count(obj, 'Extension')

    def get_revision_count(self, obj):
        return self._contract_count(obj, 'Revision')

    def get_renewal_count(self, obj):
        return self._contract_count(obj, 'Renewal')

    def validate(self, attrs):
        """employees/views.add_employee and .edit_employee both refuse an empty
        designation or email before the row is written.

        The model fields are blank=True, so DRF would happily accept them;
        re-running the template's two checks here keeps the API from creating a
        row the Django form would have rejected.
        """
        instance = self.instance
        designation = attrs.get(
            'designation', instance.designation if instance else None)
        email = attrs.get('email', instance.email if instance else None)
        errors = {}
        if not (designation or '').strip():
            errors['designation'] = 'Designation is required.'
        if not (email or '').strip():
            errors['email'] = 'Email address is required.'
        if errors:
            raise serializers.ValidationError(errors)

        # `request.POST.get("gender") or None` (and the same for tin / phone):
        # a blank cell is stored as SQL NULL, not as an empty string.
        for field in ('gender', 'tin', 'phone'):
            if field in attrs and attrs[field] == '':
                attrs[field] = None
        attrs['email'] = (attrs.get('email') or '').strip()
        attrs['designation'] = (attrs.get('designation') or '').strip()
        return attrs


# Payslip Serializers
class PayslipSerializer(serializers.ModelSerializer):
    # `gross_salary` / `net_salary` are computed properties, not columns, so
    # they must be declared explicitly -- `fields = '__all__'` only picks up
    # real model fields.
    gross_salary = serializers.SerializerMethodField()
    net_salary = serializers.SerializerMethodField()

    class Meta:
        model = Payslip
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

    def get_gross_salary(self, obj):
        return str(obj.gross_salary)

    def get_net_salary(self, obj):
        return str(obj.net_salary)


class PayslipRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayslipRequest
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class PayslipCreateSerializer(serializers.ModelSerializer):
    """Mirrors payslip/views.create_payslip.

    The form posts a single `basic_salary` figure which the view treats as the
    *total* salary and then splits 50/30/10/10 into the four allowance columns.
    Saving the posted `basic_salary` straight through would store the total as
    the basic component and leave the allowances at zero, so the split is
    reproduced here instead.

    The split columns, `id` (for the success panel's PDF link) and the two
    computed totals are echoed back so `form.html`'s created_payslip block can
    be rendered from the response alone.
    """

    gross_salary = serializers.SerializerMethodField()
    net_salary = serializers.SerializerMethodField()

    class Meta:
        model = Payslip
        fields = [
            'id', 'pin', 'name', 'designation', 'gender', 'tin', 'month',
            'year', 'project', 'branch', 'basic_salary', 'house_rent',
            'medical_allowance', 'conveyance', 'transport', 'income_tax',
            'other_deduction', 'gross_salary', 'net_salary',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        total = float(validated_data.get('basic_salary') or 0)
        validated_data['basic_salary'] = total * 0.50
        validated_data['house_rent'] = total * 0.30
        validated_data['medical_allowance'] = total * 0.10
        validated_data['conveyance'] = total * 0.10
        return super().create(validated_data)

    def get_gross_salary(self, obj):
        return str(obj.gross_salary)

    def get_net_salary(self, obj):
        return str(obj.net_salary)


class ContractEmailSerializer(serializers.Serializer):
    """POST body for contracts/views.send_contract_email."""
    recipient = serializers.EmailField(required=False, allow_blank=True)
    subject = serializers.CharField(required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ContractBulkEmailSerializer(serializers.Serializer):
    """POST body for contracts/views.bulk_email_contracts."""
    contract_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False)
    subject = serializers.CharField(required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ContractEmailLogSerializer(serializers.ModelSerializer):
    """contracts' own EmailLog -- distinct from notifications' (see the import
    note in views.py)."""

    class Meta:
        model = ContractEmailLog
        fields = '__all__'
        read_only_fields = ['id', 'sent_at']


class ContractEmailConfigSerializer(serializers.ModelSerializer):
    """contracts' own EmailConfig row."""

    class Meta:
        model = ContractEmailConfig
        fields = '__all__'
        read_only_fields = ['id']


# Portal Config Serializers
class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = '__all__'


class FormFieldSerializer(serializers.ModelSerializer):
    field_type_display = serializers.CharField(
        source='get_field_type_display', read_only=True)
    # Override DRF's SlugField: the admin form normalises `key` itself (spaces
    # and hyphens become underscores, then the alnum check runs). Left alone,
    # the slug validator fires first and would reject "Cost Centre" before
    # clean_key ever saw it -- the API would refuse a field the template saves.
    key = serializers.CharField(max_length=60)

    class Meta:
        model = FormField
        fields = '__all__'

    def validate(self, attrs):
        """Validate through portal_config's own admin form.

        `portal_config.views.field_edit` normalises `key` and refuses an
        `is_system` tick for a key the requisition model has no column for.
        Running that exact form here means the API can never accept a field the
        template would have rejected -- one source of truth, no drift.
        """
        from portal_config.views import _field_form

        instance = self.instance
        if instance is None:
            module = attrs.get('module')
            if module is None:
                return attrs
            # Anchor a brand-new field on its module so `_field_form`'s
            # `self.instance.module_id` check can run.
            instance = FormField(module=module)

        # Probe unbound to learn the form's field names, then bind only those.
        probe = _field_form(None, instance)
        data = {}
        for name in probe.fields:
            data[name] = attrs[name] if name in attrs else getattr(instance, name, None)

        form = _field_form(data, instance)
        if not form.is_valid():
            raise serializers.ValidationError(dict(form.errors))

        # `key` came back normalised -- carry it into validated_data.
        attrs['key'] = form.cleaned_data['key']
        return attrs


class WorkflowStageSerializer(serializers.ModelSerializer):
    # `approver_role` is blank for "any approver", and its choices come from a
    # callable, so resolve the label here rather than in the client.
    approver_role_display = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowStage
        fields = '__all__'

    def get_approver_role_display(self, obj):
        return obj.get_approver_role_display() if obj.approver_role else None


# Notifications Serializers
class AuditLogSerializer(serializers.ModelSerializer):
    # `performed_by` is nullable (public form submissions have no user), so a
    # dotted source would raise on NULL rows. Read it defensively instead.
    user_name = serializers.SerializerMethodField()  # raw, null for public/system
    performed_by_display = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    req_type_display = serializers.CharField(source='get_req_type_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

    def get_user_name(self, obj):
        return obj.performed_by.username if obj.performed_by_id else None

    def get_performed_by_display(self, obj):
        # No fallback baked in: history.html renders "Public submitter" while
        # audit_log.html renders "System", so each page picks its own default.
        return obj.performed_by.username if obj.performed_by_id else None


class NotificationEmailLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationEmailLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at']