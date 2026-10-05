from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from transport_requisition.models import TransportRequisition, Vehicle, Driver
from meetspace.models import Booking, Room, Announcement
from ict_requisition.models import ICTRequisition
from internal_requisition.models import InternalRequisition
from contracts.models import Contract
from employees.models import Employee
from payslip.models import Payslip, PayslipRequest
from portal_config.models import Module, FormField, WorkflowStage
# See the note in serializers.py: the sidebar email pages use the
# notifications models, not contracts' own EmailConfig/EmailLog.
from notifications.models import (
    AuditLog, EmailConfig, EmailLog,
    EmailLog as NotificationEmailLog,
)

from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer, ChangePasswordSerializer,
    VehicleSerializer, DriverSerializer,
    TransportRequisitionListSerializer, TransportRequisitionDetailSerializer,
    TransportRequisitionCreateSerializer, TransportRequisitionUpdateSerializer,
    TransportRequisitionActionSerializer, TransportTrackSerializer,
    TransportHistorySerializer, TransportReportSerializer,
    RoomSerializer, BookingListSerializer, BookingDetailSerializer,
    BookingCreateSerializer, BookingActionSerializer, AnnouncementSerializer,
    ICTRequisitionListSerializer, ICTRequisitionDetailSerializer,
    ICTRequisitionCreateSerializer, ICTRequisitionActionSerializer,
    InternalRequisitionListSerializer, InternalRequisitionDetailSerializer,
    InternalRequisitionCreateSerializer, InternalRequisitionActionSerializer,
    ContractSerializer, EmailConfigSerializer, EmailLogSerializer,
    EmployeeSerializer, PayslipSerializer, PayslipRequestSerializer,
    ModuleSerializer, FormFieldSerializer, WorkflowStageSerializer,
    AuditLogSerializer, NotificationEmailLogSerializer,
)
from .permissions import (
    IsAdminUser, IsSupervisor, IsGrants, IsTransportAdmin,
    IsICTAdmin, IsInternalAdmin, IsHRAdmin, IsRequester, IsOwnerOrAdmin,
)


User = get_user_model()


# Auth Views
class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = User.objects.get(username=request.data.get('username'))
            response.data['user'] = UserSerializer(user).data
        return response


class CustomTokenRefreshView(TokenRefreshView):
    pass


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'detail': 'Logged out successfully.'})
        except Exception:
            return Response({'detail': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'old_password': 'Current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'detail': 'Password changed successfully.'})


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


# User ViewSet
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def pending_approval(self, request):
        users = User.objects.filter(is_active=False)
        return Response(UserSerializer(users, many=True).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        user = self.get_object()
        user.delete()
        return Response({'detail': 'User rejected and deleted.'})


# Transport Requisition ViewSet
class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsTransportAdmin | IsAdminUser]


class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [IsTransportAdmin | IsAdminUser]


class TransportRequisitionViewSet(viewsets.ModelViewSet):
    queryset = TransportRequisition.objects.select_related('user', 'vehicle', 'driver').all()
    permission_classes = [IsRequester]

    def get_serializer_class(self):
        if self.action == 'list':
            return TransportRequisitionListSerializer
        if self.action == 'create':
            return TransportRequisitionCreateSerializer
        if self.action in ['update', 'partial_update']:
            return TransportRequisitionUpdateSerializer
        return TransportRequisitionDetailSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_admin() or user.is_transport_admin() or user.is_supervisor() or user.is_grants():
            return qs
        return qs.filter(user=user)

    def get_permissions(self):
        if self.action in ['create']:
            return [IsRequester()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrAdmin()]
        if self.action in ['approve', 'decline', 'amend', 'assign']:
            return [IsTransportAdmin | IsGrants | IsSupervisor | IsAdminUser()]
        return [IsRequester()]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        requisition = self.get_object()
        serializer = TransportRequisitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if requisition.status not in ['pending_first', 'pending_grants', 'pending_transport']:
            return Response({'error': 'Requisition cannot be approved in current state.'}, status=status.HTTP_400_BAD_REQUEST)

        # Simple state transitions
        if requisition.status == 'pending_first':
            requisition.status = 'pending_grants'
        elif requisition.status == 'pending_grants':
            requisition.status = 'pending_transport'
        elif requisition.status == 'pending_transport':
            requisition.status = 'approved'
        requisition.save()

        # Log audit
        AuditLog.objects.create(
            user=request.user,
            action='approve',
            content_object=requisition,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(TransportRequisitionDetailSerializer(requisition).data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        requisition = self.get_object()
        serializer = TransportRequisitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        requisition.status = 'rejected'
        requisition.save()

        AuditLog.objects.create(
            user=request.user,
            action='decline',
            content_object=requisition,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(TransportRequisitionDetailSerializer(requisition).data)

    @action(detail=True, methods=['post'])
    def amend(self, request, pk=None):
        requisition = self.get_object()
        serializer = TransportRequisitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not (request.user.is_grants() or request.user.is_admin()):
            return Response({'error': 'Only Grants can amend.'}, status=status.HTTP_403_FORBIDDEN)

        if serializer.validated_data.get('project_code'):
            requisition.project_code = serializer.validated_data['project_code']
        if serializer.validated_data.get('budget_code'):
            requisition.budget_code = serializer.validated_data['budget_code']
        requisition.save()

        AuditLog.objects.create(
            user=request.user,
            action='amend',
            content_object=requisition,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(TransportRequisitionDetailSerializer(requisition).data)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        requisition = self.get_object()
        serializer = TransportRequisitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not (request.user.is_transport_admin() or request.user.is_admin()):
            return Response({'error': 'Only Transport Admin can assign.'}, status=status.HTTP_403_FORBIDDEN)

        vehicle_id = serializer.validated_data.get('vehicle_id')
        driver_id = serializer.validated_data.get('driver_id')

        if vehicle_id:
            requisition.vehicle_id = vehicle_id
        if driver_id:
            requisition.driver_id = driver_id

        requisition.status = 'assigned'
        requisition.save()

        AuditLog.objects.create(
            user=request.user,
            action='assign',
            content_object=requisition,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(TransportRequisitionDetailSerializer(requisition).data)

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        qs = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser | IsTransportAdmin])
    def pending(self, request):
        qs = self.get_queryset().filter(status__in=['pending_first', 'pending_grants', 'pending_transport'])
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


# MeetSpace ViewSets
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsHRAdmin | IsAdminUser]


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related('room', 'user').all()
    permission_classes = [IsRequester]

    def get_serializer_class(self):
        if self.action == 'list':
            return BookingListSerializer
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingDetailSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_admin() or user.is_hr_admin():
            return qs
        if user.is_authenticated:
            return qs.filter(Q(user=user) | Q(email__iexact=user.email))
        return qs.none()

    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.AllowAny()]  # Public booking
        if self.action in ['approve', 'decline', 'suggest_alternative']:
            return [IsHRAdmin | IsAdminUser()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrAdmin()]
        return [IsRequester()]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        booking = self.get_object()
        serializer = BookingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking.status = 'approved'
        booking.save()

        AuditLog.objects.create(
            user=request.user,
            action='approve',
            content_object=booking,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(BookingDetailSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        booking = self.get_object()
        serializer = BookingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking.status = 'rejected'
        booking.save()

        AuditLog.objects.create(
            user=request.user,
            action='decline',
            content_object=booking,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(BookingDetailSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def suggest_alternative(self, request, pk=None):
        booking = self.get_object()
        serializer = BookingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create alternative booking suggestion
        # This would need a separate model in production
        booking.status = 'alternative_suggested'
        booking.save()

        AuditLog.objects.create(
            user=request.user,
            action='suggest_alternative',
            content_object=booking,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(BookingDetailSerializer(booking).data)

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        qs = self.get_queryset().filter(Q(user=request.user) | Q(email__iexact=request.user.email))
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def availability(self, request):
        room_id = request.query_params.get('room_id')
        start = request.query_params.get('start')
        end = request.query_params.get('end')

        if not all([room_id, start, end]):
            return Response({'error': 'room_id, start, end required'}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils.dateparse import parse_datetime
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)

        conflicts = Booking.objects.filter(
            room_id=room_id,
            status__in=['pending', 'approved'],
            start_time__lt=end_dt,
            end_time__gt=start_dt,
        ).exists()

        return Response({'available': not conflicts})


class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsHRAdmin | IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ICT Requisition ViewSet
class ICTRequisitionViewSet(viewsets.ModelViewSet):
    queryset = ICTRequisition.objects.select_related('user').all()
    permission_classes = [IsRequester]

    def get_serializer_class(self):
        if self.action == 'list':
            return ICTRequisitionListSerializer
        if self.action == 'create':
            return ICTRequisitionCreateSerializer
        return ICTRequisitionDetailSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_admin() or user.is_ict_admin():
            return qs
        return qs.filter(user=user)

    def get_permissions(self):
        if self.action in ['approve', 'decline']:
            return [IsICTAdmin | IsAdminUser()]
        return [IsRequester()]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        req = self.get_object()
        serializer = ICTRequisitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req.status = 'approved'
        req.save()

        AuditLog.objects.create(
            user=request.user,
            action='approve',
            content_object=req,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(ICTRequisitionDetailSerializer(req).data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        req = self.get_object()
        serializer = ICTRequisitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req.status = 'rejected'
        req.save()

        AuditLog.objects.create(
            user=request.user,
            action='decline',
            content_object=req,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(ICTRequisitionDetailSerializer(req).data)

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        qs = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


# Internal Requisition ViewSet
class InternalRequisitionViewSet(viewsets.ModelViewSet):
    queryset = InternalRequisition.objects.select_related('user').all()
    permission_classes = [IsRequester]

    def get_serializer_class(self):
        if self.action == 'list':
            return InternalRequisitionListSerializer
        if self.action == 'create':
            return InternalRequisitionCreateSerializer
        return InternalRequisitionDetailSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_admin() or user.is_internal_admin():
            return qs
        return qs.filter(user=user)

    def get_permissions(self):
        if self.action in ['approve', 'decline']:
            return [IsInternalAdmin | IsAdminUser()]
        return [IsRequester()]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        req = self.get_object()
        serializer = InternalRequisitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req.status = 'approved'
        req.save()

        AuditLog.objects.create(
            user=request.user,
            action='approve',
            content_object=req,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(InternalRequisitionDetailSerializer(req).data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        req = self.get_object()
        serializer = InternalRequisitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req.status = 'rejected'
        req.save()

        AuditLog.objects.create(
            user=request.user,
            action='decline',
            content_object=req,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(InternalRequisitionDetailSerializer(req).data)

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        qs = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


# Contracts ViewSets
class ContractViewSet(viewsets.ModelViewSet):
    # Contract is keyed by `pin`, not by a FK to Employee -- there is nothing
    # to select_related here.
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    permission_classes = [IsHRAdmin | IsAdminUser]


class EmailConfigViewSet(viewsets.ModelViewSet):
    queryset = EmailConfig.objects.all()
    serializer_class = EmailConfigSerializer
    permission_classes = [IsAdminUser]


class EmailLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EmailLog.objects.all()
    serializer_class = EmailLogSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        # The Django page shows the most recent 100 and nothing older.
        return EmailLog.objects.all()[:100]

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({
            'count': EmailLog.objects.count(),
            'failed_count': EmailLog.objects.filter(status='failed').count(),
            'results': serializer.data,
        })

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Re-send one failed approval request -- mirrors notifications.views.retry_email."""
        from notifications.views import _get_req_model
        from notifications.utils import send_approval_request

        log = self.get_object()
        if log.status == EmailLog.Status.SUCCESS:
            return Response({'detail': 'This email was already sent successfully.'})

        if not (log.email_type == 'approval_request' and log.req_type and log.req_id):
            return Response({'detail': 'Cannot retry this email automatically.'},
                            status=status.HTTP_400_BAD_REQUEST)

        model = _get_req_model(log.req_type)
        if not model:
            return Response({'detail': 'Unknown requisition type.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            requisition = model.objects.get(pk=log.req_id)
        except model.DoesNotExist:
            return Response({'detail': 'Requisition not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        # The requisition's own status is the stage it is sitting at, so the
        # reminder goes to whoever owns that stage.
        send_approval_request(log.department, requisition, log.req_type,
                              requisition.status)
        return Response({'detail': f'Retry initiated for #{log.req_id}.'})

    @action(detail=False, methods=['post'])
    def retry_all(self, request):
        """Re-send every failed approval request -- mirrors retry_all_failed."""
        from notifications.views import _get_req_model
        from notifications.utils import send_approval_request

        retried = 0
        for log in EmailLog.objects.filter(status=EmailLog.Status.FAILED):
            if not (log.email_type == 'approval_request' and log.req_type and log.req_id):
                continue
            model = _get_req_model(log.req_type)
            if not model:
                continue
            try:
                requisition = model.objects.get(pk=log.req_id)
            except model.DoesNotExist:
                continue
            send_approval_request(log.department, requisition, log.req_type,
                                  requisition.status)
            retried += 1
        return Response({'detail': f'Retried {retried} failed email(s).'})


# Employees ViewSet
class EmployeeViewSet(viewsets.ModelViewSet):
    # Employee has no FK to User (it is keyed by PIN); its only relation is the
    # reverse `employeesalary`, so no join is possible here.
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsHRAdmin | IsAdminUser]


# Payslip ViewSets
class PayslipViewSet(viewsets.ModelViewSet):
    # Payslip has no relations at all -- it is a flat row keyed by PIN.
    queryset = Payslip.objects.all()
    serializer_class = PayslipSerializer
    permission_classes = [IsHRAdmin | IsAdminUser]


class PayslipRequestViewSet(viewsets.ModelViewSet):
    # PayslipRequest is also relation-free (name / pin / months / year).
    queryset = PayslipRequest.objects.all()
    serializer_class = PayslipRequestSerializer
    permission_classes = [IsRequester]


# Portal Config ViewSets
class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [IsAdminUser]


class FormFieldViewSet(viewsets.ModelViewSet):
    queryset = FormField.objects.all()
    serializer_class = FormFieldSerializer
    permission_classes = [IsAdminUser]


class WorkflowStageViewSet(viewsets.ModelViewSet):
    queryset = WorkflowStage.objects.all()
    serializer_class = WorkflowStageSerializer
    permission_classes = [IsAdminUser]


# Notifications ViewSets
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    # The actor FK is `performed_by` -- AuditLog has no `user` field.
    queryset = AuditLog.objects.select_related('performed_by').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]


class NotificationEmailLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NotificationEmailLog.objects.all()
    serializer_class = NotificationEmailLogSerializer
    permission_classes = [IsAdminUser]


# Dashboard / Stats Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    user = request.user
    stats = {}

    if user.is_admin():
        stats = {
            'transport': {
                'total': TransportRequisition.objects.count(),
                'pending': TransportRequisition.objects.filter(status__in=['pending_first', 'pending_grants', 'pending_transport']).count(),
            },
            'meetspace': {
                'total': Booking.objects.count(),
                'pending': Booking.objects.filter(status='pending').count(),
            },
            'ict': {
                'total': ICTRequisition.objects.count(),
                'pending': ICTRequisition.objects.filter(status__in=['pending']).count(),
            },
            'internal': {
                'total': InternalRequisition.objects.count(),
                'pending': InternalRequisition.objects.filter(status__in=['pending']).count(),
            },
            'pending_users': User.objects.filter(is_active=False).count(),
        }
    elif user.is_transport_admin():
        stats = {
            'transport': {
                'total': TransportRequisition.objects.count(),
                'pending': TransportRequisition.objects.filter(status__in=['pending_first', 'pending_grants', 'pending_transport']).count(),
            },
        }
    elif user.is_ict_admin():
        stats = {
            'ict': {
                'total': ICTRequisition.objects.count(),
                'pending': ICTRequisition.objects.filter(status__in=['pending']).count(),
            },
        }
    elif user.is_internal_admin():
        stats = {
            'internal': {
                'total': InternalRequisition.objects.count(),
                'pending': InternalRequisition.objects.filter(status__in=['pending']).count(),
            },
        }
    elif user.is_hr_admin():
        stats = {
            'meetspace': {
                'total': Booking.objects.count(),
                'pending': Booking.objects.filter(status='pending').count(),
            },
        }
    else:
        stats = {
            'my_requests': {
                'transport': TransportRequisition.objects.filter(user=user).count(),
                'ict': ICTRequisition.objects.filter(user=user).count(),
                'internal': InternalRequisition.objects.filter(user=user).count(),
                'bookings': Booking.objects.filter(Q(user=user) | Q(email__iexact=user.email)).count(),
            }
        }

    return Response(stats)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def transport_track(request):
    """Public self-service status lookup by email address.

    Mirrors ``transport_requisition.views.track_view``: only requisitions whose
    ``email_address`` matches exactly (case-insensitive) are returned, so this
    cannot be used to enumerate other people's requests.
    """
    email = (request.query_params.get('email') or '').strip()
    if not email:
        return Response({'detail': 'Enter the email address you used.'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_email(email)
    except ValidationError:
        return Response({'detail': 'Enter a valid email address.'},
                        status=status.HTTP_400_BAD_REQUEST)

    requisitions = TransportRequisition.objects.filter(
        email_address__iexact=email
    ).order_by('-created_at')
    return Response(TransportTrackSerializer(requisitions, many=True).data)


def _transport_stage_options():
    """The configured approval chain, for the status filter dropdown.

    Built from the workflow engine exactly as the Django templates do it, so a
    newly added stage shows up here without touching this file.
    """
    from portal_config import engine
    return [{'key': s.key, 'name': s.name} for s in engine.get_stages('transport')]


@api_view(['GET'])
@permission_classes([IsRequester])
def my_requisitions(request):
    """Every requisition the signed-in user owns, newest first.

    Reuses the Django view's own REQUISITION_TYPES / STATUS_LABELS maps so the
    labels here can never drift from ``templates/my_requisitions.html``.
    """
    from requisition_portal.views import REQUISITION_TYPES, STATUS_LABELS, visible_types

    items = []
    for key in visible_types():
        model, label, icon, field, _url_name = REQUISITION_TYPES[key]
        for r in model.objects.filter(user=request.user).values(
                'pk', 'request_number', field, 'status', 'created_at'):
            raw = r[field] or ''
            items.append({
                # `d M Y`, matching the template's `{{ item.created_at|date:"d M Y" }}`.
                # Kept alongside the raw datetime so sorting happens on the real
                # value -- formatted strings would sort wrongly across months.
                'created_at': r['created_at'].strftime('%d %b %Y'),
                '_ts': r['created_at'],
                'id': r['pk'],
                'type': label,
                'type_icon': icon,
                'request_number': r['request_number'],
                'summary': raw.split('\n')[0][:60],
                'status': r['status'],
                'status_label': STATUS_LABELS.get(r['status'], r['status']),
                'url': key,
            })

    items.sort(key=lambda x: x['_ts'], reverse=True)
    for item in items:
        del item['_ts']
    return Response(items)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def portal_choices(request):
    """Choice lists the admin configurators render.

    Read from the models themselves so the Workflow Editor and Email Settings
    pages can never offer a choice the backend would reject.
    """
    from accounts.models import User
    from notifications.models import Department
    from portal_config.models import StageAction

    return Response({
        'roles': [{'value': v, 'label': l} for v, l in User.Role.choices],
        'stage_actions': [{'value': a.value, 'label': a.label} for a in StageAction],
        'departments': [{'value': v, 'label': l} for v, l in Department.choices],
    })


@api_view(['GET'])
@permission_classes([IsTransportAdmin])
def transport_history(request):
    """Admin-only tracking history: every request plus its audit trail.

    Mirrors ``transport_requisition.views.history_view``, filters included.
    """
    qs = TransportRequisition.objects.all().order_by('-created_at')
    search = (request.query_params.get('q') or '').strip()
    status_filter = request.query_params.get('status') or ''
    date_from = request.query_params.get('date_from') or ''
    date_to = request.query_params.get('date_to') or ''

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

    # One query for the whole result set, then attach per row so the serializer
    # can iterate directly (the template does the same thing).
    trail = {}
    if requisitions:
        for entry in AuditLog.objects.filter(
                req_type='transport', req_id__in=[r.pk for r in requisitions]
        ).order_by('created_at'):
            trail.setdefault(entry.req_id, []).append(entry)
    for r in requisitions:
        r.trail = trail.get(r.pk, [])

    return Response({
        'counts': {
            'total': TransportRequisition.objects.count(),
            'pending': TransportRequisition.objects.filter(
                status__in=TransportRequisition.PENDING_STATUSES).count(),
            'approved': TransportRequisition.objects.filter(
                status__in=['approved', 'assigned']).count(),
            'rejected': TransportRequisition.objects.filter(
                status='rejected').count(),
            'public': TransportRequisition.objects.filter(user__isnull=True).count(),
        },
        'stages': _transport_stage_options(),
        'results': TransportHistorySerializer(requisitions, many=True).data,
    })


def _transport_report_qs(request):
    """Apply the report's date/status filters -- shared by the view and its export."""
    qs = TransportRequisition.objects.all()
    date_from = request.query_params.get('date_from') or ''
    date_to = request.query_params.get('date_to') or ''
    status_filter = request.query_params.get('status') or ''

    if date_from:
        qs = qs.filter(pick_up_date__gte=date_from)
    if date_to:
        qs = qs.filter(pick_up_date__lte=date_to)
    if status_filter:
        qs = qs.filter(status=status_filter)
    return qs


@api_view(['GET'])
@permission_classes([IsTransportAdmin])
def transport_report(request):
    """Filtered report over transport requisitions.

    Mirrors ``transport_requisition.views.report_view``: the date filters apply
    to `pick_up_date` (not `created_at`), matching the original.
    """
    qs = _transport_report_qs(request)

    return Response({
        'counts': {
            'total': qs.count(),
            'approved': qs.filter(status__in=['approved', 'assigned']).count(),
            'rejected': qs.filter(status='rejected').count(),
            'pending': qs.filter(status__in=list(TransportRequisition.PENDING_STATUSES)).count(),
        },
        'stages': _transport_stage_options(),
        'results': TransportReportSerializer(qs, many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsTransportAdmin])
def transport_report_export(request):
    """Excel export of whatever the report is currently filtered to.

    Mirrors ``transport_requisition.views.export_excel_view`` -- same headers,
    same column order, same header styling. Returned as a plain file response
    so the browser can save it directly.
    """
    import io
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side
    from django.http import HttpResponse

    qs = _transport_report_qs(request)

    headers = [
        'Request #', 'Name', 'Email', 'Mobile', 'Designation', 'PIN', 'Passengers',
        'Vehicle Type', 'Pick-up Date', 'Pick-up Time', 'Pick-up Location',
        'Destination', 'Drop-off Date', 'Drop-off Time', 'Drop-off Location',
        'Travelling Reason', 'Project Name/Code', 'Budget Code',
        'Driver', 'Car No', 'Driver Cell', 'Status',
    ]

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = openpyxl.styles.PatternFill(
        start_color='D97706', end_color='D97706', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin'),
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Transport Requisitions'

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border

    for row, r in enumerate(qs, 2):
        data = [
            r.request_number, r.full_name, r.email_address, r.mobile_number,
            r.designation, r.pin, r.num_passengers, r.get_vehicle_type_display(),
            r.pick_up_date, str(r.pick_up_time), r.pick_up_location,
            r.destination, r.drop_off_date, str(r.drop_off_time), r.drop_off_location,
            r.travelling_reason, r.project_name_code, r.budget_code,
            r.driver.name if r.driver_id else '',
            r.driver.car_no if r.driver_id else '',
            r.driver.cell_number if r.driver_id else '',
            r.get_status_display(),
        ]
        for col, val in enumerate(data, 1):
            ws.cell(row=row, column=col, value=val).border = thin_border

    for col in range(1, len(headers) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 18

    buffer = io.BytesIO()
    wb.save(buffer)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = (
        'attachment; '
        f'filename="transport_requisitions_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    )
    return response


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_modules(request):
    """Return the modules shown on the public landing page.

    Mirrors the ``visible_modules`` context the Django landing template gates
    its cards on: ``is_enabled`` is the routing switch, ``is_visible`` is what
    the UI shows.
    """
    from portal_config.engine import visible_module_keys

    modules = Module.objects.filter(key__in=visible_module_keys()).order_by('order')
    return Response(ModuleSerializer(modules, many=True).data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def module_form_fields(request, module_key):
    """Return form fields for a specific module."""
    try:
        module = Module.objects.get(key=module_key, is_enabled=True)
    except Module.DoesNotExist:
        return Response({'error': 'Module not found'}, status=status.HTTP_404_NOT_FOUND)

    # FormField has no `is_active` column -- the module's own switch is what
    # gates routing, so order the whole chain here instead.
    fields = FormField.objects.filter(module=module).order_by('step', 'order')
    return Response(FormFieldSerializer(fields, many=True).data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def module_workflow(request, module_key):
    """Return workflow stages for a specific module."""
    try:
        module = Module.objects.get(key=module_key, is_enabled=True)
    except Module.DoesNotExist:
        return Response({'error': 'Module not found'}, status=status.HTTP_404_NOT_FOUND)

    stages = WorkflowStage.objects.filter(module=module).order_by('order')
    return Response(WorkflowStageSerializer(stages, many=True).data)