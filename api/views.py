from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

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

from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer, ChangePasswordSerializer,
    VehicleSerializer, DriverSerializer,
    TransportRequisitionListSerializer, TransportRequisitionDetailSerializer,
    TransportRequisitionCreateSerializer, TransportRequisitionUpdateSerializer,
    TransportRequisitionActionSerializer,
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
    queryset = Contract.objects.select_related('employee').all()
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


# Employees ViewSet
class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related('user').all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsHRAdmin | IsAdminUser]


# Payslip ViewSets
class PayslipViewSet(viewsets.ModelViewSet):
    queryset = Payslip.objects.select_related('employee').all()
    serializer_class = PayslipSerializer
    permission_classes = [IsHRAdmin | IsAdminUser]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_admin() or user.is_hr_admin():
            return qs
        return qs.filter(employee__user=user)


class PayslipRequestViewSet(viewsets.ModelViewSet):
    queryset = PayslipRequest.objects.select_related('employee').all()
    serializer_class = PayslipRequestSerializer
    permission_classes = [IsRequester]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_admin() or user.is_hr_admin():
            return qs
        return qs.filter(employee__user=user)

    def perform_create(self, serializer):
        # Get employee for current user
        try:
            employee = Employee.objects.get(user=self.request.user)
            serializer.save(employee=employee)
        except Employee.DoesNotExist:
            serializer.save()


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
    queryset = AuditLog.objects.select_related('user').all()
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

    fields = FormField.objects.filter(module=module, is_active=True).order_by('step', 'order')
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