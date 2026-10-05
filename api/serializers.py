from rest_framework import serializers
from accounts.models import User
from transport_requisition.models import TransportRequisition, Vehicle, Driver
from meetspace.models import Booking, Room, Announcement
from ict_requisition.models import ICTRequisition
from internal_requisition.models import InternalRequisition
from contracts.models import Contract
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
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'password',
            'password_confirm', 'role', 'phone',
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'role', 'phone', 'is_active',
        ]


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
    action = serializers.ChoiceField(choices=['approve', 'decline', 'amend', 'assign'])
    comment = serializers.CharField(required=False, allow_blank=True)
    # For amend action
    project_code = serializers.CharField(required=False, allow_blank=True)
    budget_code = serializers.CharField(required=False, allow_blank=True)
    # For assign action
    vehicle_id = serializers.IntegerField(required=False, allow_null=True)
    driver_id = serializers.IntegerField(required=False, allow_null=True)


# MeetSpace Serializers
class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'


class BookingListSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='room.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'room', 'room_name', 'user', 'user_name', 'email_address',
            'meeting_title', 'start_time', 'end_time', 'status', 'status_display',
            'created_at', 'updated_at',
        ]


class BookingDetailSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            'room', 'meeting_title', 'requirements', 'start_time', 'end_time',
            'email_address', 'number_of_participants',
        ]

    def create(self, validated_data):
        if self.context['request'].user.is_authenticated:
            validated_data['user'] = self.context['request'].user
            validated_data['email_address'] = self.context['request'].user.email
        return super().create(validated_data)


class BookingActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'decline', 'suggest_alternative'])
    comment = serializers.CharField(required=False, allow_blank=True)
    # For suggest_alternative
    alternative_room_id = serializers.IntegerField(required=False, allow_null=True)
    alternative_start_time = serializers.DateTimeField(required=False, allow_null=True)
    alternative_end_time = serializers.DateTimeField(required=False, allow_null=True)


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


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
    action = serializers.ChoiceField(choices=['approve', 'decline'])
    comment = serializers.CharField(required=False, allow_blank=True)


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
    action = serializers.ChoiceField(choices=['approve', 'decline'])
    comment = serializers.CharField(required=False, allow_blank=True)


# Contracts Serializers
class ContractSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_contract_type_display', read_only=True)

    class Meta:
        model = Contract
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


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

    class Meta:
        model = Employee
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

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


# Portal Config Serializers
class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = '__all__'


class FormFieldSerializer(serializers.ModelSerializer):
    field_type_display = serializers.CharField(
        source='get_field_type_display', read_only=True)

    class Meta:
        model = FormField
        fields = '__all__'


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