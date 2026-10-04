from rest_framework import serializers
from accounts.models import User
from transport_requisition.models import TransportRequisition, Vehicle, Driver
from meetspace.models import Booking, Room, Announcement
from ict_requisition.models import ICTRequisition
from internal_requisition.models import InternalRequisition
from contracts.models import Contract, EmailConfig, EmailLog
from employees.models import Employee
from payslip.models import Payslip, PayslipRequest
from portal_config.models import Module, FormField, WorkflowStage
from notifications.models import AuditLog, EmailLog as NotificationEmailLog


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
            'id', 'request_number', 'user', 'user_name', 'user_email',
            'destination', 'travelling_reason', 'pick_up_date', 'pick_up_time',
            'drop_off_date', 'drop_off_time', 'num_passengers', 'status',
            'status_display', 'vehicle', 'vehicle_name', 'driver', 'driver_name',
            'created_at', 'updated_at',
        ]


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
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Contract
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmailConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailConfig
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmailLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


# Employees Serializers
class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Employee
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# Payslip Serializers
class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = Payslip
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PayslipRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PayslipRequest
        fields = '__all__'
        read_only_fields = ['id', 'employee', 'created_at', 'updated_at']


# Portal Config Serializers
class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = '__all__'


class FormFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormField
        fields = '__all__'


class WorkflowStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStage
        fields = '__all__'


# Notifications Serializers
class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class NotificationEmailLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationEmailLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at']