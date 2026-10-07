from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q, Count
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import date, datetime, timedelta

from accounts.models import User
from transport_requisition.models import TransportRequisition, Vehicle, Driver
from meetspace.models import Booking, Room, Announcement
from ict_requisition.models import ICTRequisition
from internal_requisition.models import InternalRequisition
from contracts.models import Contract
# The HR shell has its own EmailConfig / EmailLog tables — distinct from the
# notifications ones imported below, which back the portal sidebar's email
# pages. Aliased so both can be used in one module.
from contracts.models import (
    EmailConfig as ContractEmailConfig,
    EmailLog as ContractEmailLog,
)
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
    BookingCreateSerializer, BookingActionSerializer, BookingTrackSerializer,
    AnnouncementSerializer,
    ICTRequisitionListSerializer, ICTRequisitionDetailSerializer,
    ICTRequisitionCreateSerializer, ICTRequisitionActionSerializer,
    InternalRequisitionListSerializer, InternalRequisitionDetailSerializer,
    InternalRequisitionCreateSerializer, InternalRequisitionActionSerializer,
    ContractSerializer, EmailConfigSerializer, EmailLogSerializer,
    EmployeeSerializer, PayslipSerializer, PayslipRequestSerializer,
    PayslipCreateSerializer, ContractEmailSerializer,
    ContractBulkEmailSerializer, ContractEmailLogSerializer,
    ContractEmailConfigSerializer,
    ModuleSerializer, FormFieldSerializer, WorkflowStageSerializer,
    AuditLogSerializer, NotificationEmailLogSerializer,
    NotificationTrackSerializer,
)
from .permissions import (
    IsAdminUser, IsSupervisor, IsGrants, IsTransportAdmin,
    IsICTAdmin, IsInternalAdmin, IsHRAdmin, IsRequester, IsOwnerOrAdmin,
)
from . import workflow


User = get_user_model()


# Auth Views
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """``accounts.views.CustomLoginView.form_invalid``.

    Self-registration (Tier 3) creates a *disabled* account, and main tells
    that user so by name rather than with a bad-password message. Checked
    before SimpleJWT's own authenticate, which would otherwise answer
    "No active account found with the given credentials" for both cases.
    """

    def validate(self, attrs):
        from rest_framework.exceptions import ValidationError

        try:
            user = User.objects.get(username=attrs.get(self.username_field))
        except User.DoesNotExist:
            user = None
        if user is not None and not user.is_active:
            raise ValidationError({
                'inactive': [
                    'Your account is pending admin approval. Please try again later.'
                ],
            })
        return super().validate(attrs)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

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
        # Same guard as ``transport_requisition.views.detail_view``: approvers
        # and admins see everything, everyone else sees their own.
        if user.is_admin() or user.is_approver():
            return qs
        return qs.filter(user=user)

    def get_permissions(self):
        if self.action in ['create']:
            return [IsRequester()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrAdmin()]
        if self.action in ['approve', 'decline', 'amend', 'assign', 'actions']:
            # The stage engine decides who may act, exactly as the template
            # views do — a coarser DRF permission here would block roles the
            # configured chain legitimately allows.
            return [IsRequester()]
        return [IsRequester()]

    @action(detail=True, methods=['get'])
    def actions(self, request, pk=None):
        """Everything the detail page needs to decide which buttons to show."""
        requisition = self.get_object()
        return Response(workflow.transport_context(request.user, requisition))

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        serializer = TransportRequisitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requisition = self.get_object()
        try:
            workflow.transport_approve(
                request.user, requisition, serializer.validated_data)
        except workflow.WorkflowError as exc:
            return Response({'error': exc.message}, status=exc.http_status)
        return Response(TransportRequisitionDetailSerializer(requisition).data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        serializer = TransportRequisitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requisition = self.get_object()
        try:
            workflow.transport_decline(
                request.user, requisition, serializer.validated_data)
        except workflow.WorkflowError as exc:
            return Response({'error': exc.message}, status=exc.http_status)
        return Response(TransportRequisitionDetailSerializer(requisition).data)

    @action(detail=True, methods=['post'])
    def amend(self, request, pk=None):
        """Kept for compatibility — amendments ride along with ``approve``."""
        return self.approve(request, pk=pk)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        serializer = TransportRequisitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requisition = self.get_object()
        try:
            workflow.transport_assign(
                request.user, requisition, serializer.validated_data)
        except workflow.WorkflowError as exc:
            return Response({'error': exc.message}, status=exc.http_status)
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
    serializer_class = RoomSerializer

    def get_queryset(self):
        """room_list.html prints `room.booking_count` -- approved bookings only."""
        # order_by re-states Room.Meta.ordering: `annotate()` drops the model's
        # default ordering, and DRF paginates this list.
        rooms = Room.objects.annotate(
            booking_count=Count('bookings', filter=Q(bookings__status=Booking.Status.APPROVED)),
        ).order_by('room_number')
        if not self.request.user.is_authenticated:
            # booking_create is a public page and offers exactly
            # `Room.objects.filter(is_active=True)` in its dropdown, so an
            # anonymous caller sees no retired rooms either.
            return rooms.filter(is_active=True)
        return rooms

    def get_permissions(self):
        # main gates only the Add/Edit/Retire buttons on _is_hr_admin (and
        # room_create/edit/toggle re-check it per view); room_list itself is
        # just @login_required. Reads therefore stay open -- and open to
        # anonymous callers too, because the public booking form builds its
        # room picker from this same list without a session.
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        # Parentheses matter: `[A | B]()` would call the *list*.
        return [(IsHRAdmin | IsAdminUser)()]


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related('room', 'user').all()
    permission_classes = [IsRequester]

    def get_serializer_class(self):
        if self.action in ['list', 'my_bookings']:
            return BookingListSerializer
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingDetailSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_admin() or user.is_hr_admin():
            return qs
        # meetspace.views.booking_list narrows to the requester's own rows and
        # nothing else -- there is no email fallback here; that is what the
        # public /track/ page is for.
        if not user.is_authenticated:
            return qs.none()
        qs = qs.filter(user=user)
        # booking_list.html submits `?status=` as a GET form; only the list
        # endpoint reads it, exactly as the template only applies it there.
        if self.action == 'list':
            status = self.request.query_params.get('status')
            if status:
                qs = qs.filter(status=status)
        return qs

    def create(self, request, *args, **kwargs):
        """Answer with the saved booking, not the create input.

        meetspace.views.booking_create renders booking_submitted.html with the
        instance it just saved -- same request, same URL, no round trip. The
        React form has to reproduce that panel too, and the caller is normally
        *anonymous*, so it has no session to read the booking back with (a
        follow-up GET /meetspace/{id}/ would 401 and bounce it to /login).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        detail = BookingDetailSerializer(booking, context=self.get_serializer_context())
        return Response(detail.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """The "New Booking Request — MeetSpace" mail main sends at views.py:285."""
        from meetspace.views import _hr_admin_emails, _notify

        booking = serializer.save()
        _notify(
            'New Booking Request — MeetSpace',
            f"New booking request from {booking.email_address}.\n"
            f"Meeting: {booking.meeting_title}\nRoom: {booking.room.room_number}\n"
            f"Date: {booking.date}\nTime: {booking.start_time}–{booking.end_time}.",
            list(_hr_admin_emails()),
        )
        return booking

    def get_permissions(self):
        if self.action in ['create', 'track']:
            # `create` is the public booking form, and `track` mirrors
            # meetspace.views.track_view, which is reached from
            # base_public.html without signing in.
            return [permissions.AllowAny()]
        if self.action in ['approve', 'decline', 'suggest_alternative',
                           'cancel', 'accept_alternative',
                           'reject_alternatives', 'actions']:
            # MeetSpace's own role rules live in the workflow helpers so they
            # stay identical to the template views (owner may cancel/answer
            # alternatives, only HR admins may approve/reject).
            return [IsRequester()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrAdmin()]
        return [IsRequester()]

    @action(detail=True, methods=['get'])
    def actions(self, request, pk=None):
        """Which MeetSpace buttons this user may see on this booking."""
        booking = self.get_object()
        return Response(workflow.booking_context(request.user, booking))

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        booking = self.get_object()
        try:
            workflow.booking_approve(request.user, booking)
        except workflow.WorkflowError as exc:
            return Response({'error': exc.message}, status=exc.http_status)
        return Response(BookingDetailSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        serializer = BookingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = self.get_object()
        try:
            workflow.booking_decline(
                request.user, booking, serializer.validated_data)
        except workflow.WorkflowError as exc:
            return Response({'error': exc.message}, status=exc.http_status)
        return Response(BookingDetailSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        serializer = BookingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = self.get_object()
        try:
            workflow.booking_cancel(
                request.user, booking, serializer.validated_data)
        except workflow.WorkflowError as exc:
            return Response({'error': exc.message}, status=exc.http_status)
        return Response(BookingDetailSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='suggest_alternative')
    def suggest_alternative(self, request, pk=None):
        serializer = BookingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = self.get_object()
        try:
            workflow.booking_suggest_alternatives(
                request.user, booking, serializer.validated_data)
        except workflow.WorkflowError as exc:
            return Response({'error': exc.message}, status=exc.http_status)
        return Response(BookingDetailSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='accept_alternative')
    def accept_alternative(self, request, pk=None):
        serializer = BookingActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = self.get_object()
        try:
            workflow.booking_accept_alternative(
                request.user, booking, serializer.validated_data)
        except workflow.WorkflowError as exc:
            return Response({'error': exc.message}, status=exc.http_status)
        return Response(BookingDetailSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='reject_alternatives')
    def reject_alternatives(self, request, pk=None):
        booking = self.get_object()
        try:
            workflow.booking_reject_alternatives(request.user, booking)
        except workflow.WorkflowError as exc:
            return Response({'error': exc.message}, status=exc.http_status)
        return Response(BookingDetailSerializer(booking).data)

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        # Built from the model rather than get_queryset(): the latter already
        # narrows to `user=<you>` for non-admins, which would erase the email
        # half of this action -- public bookings carry no user row. The field is
        # `Booking.email_address`; the shorter name raised FieldError.
        qs = Booking.objects.select_related('room', 'user').filter(
            Q(user=request.user) | Q(email_address__iexact=request.user.email))
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

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Mirror meetspace.views.dashboard -- a role-aware overview.

        An HR admin sees every booking plus room totals; anyone else sees only
        their own, which is what the view's `_is_hr_admin` branch picks between.
        The stat keys are the template's, since `dashboard.html` loops
        `stats.items` straight into cards.
        """
        today = date.today()
        bookings = Booking.objects.select_related('room', 'user')
        is_hr_admin = request.user.is_admin() or request.user.is_hr_admin()

        if is_hr_admin:
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
        return Response({
            'stats': stats,
            'recent': BookingListSerializer(recent, many=True).data,
            'announcements': AnnouncementSerializer(announcements, many=True).data,
            'is_hr_admin': is_hr_admin,
        })

    @action(detail=False, methods=['get'])
    def track(self, request):
        """Mirror meetspace.views.track_view -- public lookup by email address.

        Bookings are matched on `email_address` rather than an id, so this
        cannot be used to enumerate anybody else's reservations. The payload is
        BookingTrackSerializer, which leaves the requester record out because
        track.html never renders it.
        """
        email = (request.query_params.get('email') or '').strip()
        if not email:
            # GET with no search yet: main just re-renders the empty form.
            return Response({'searched': False, 'email': '', 'bookings': []})
        try:
            validate_email(email)
        except ValidationError:
            return Response({'error': 'Enter a valid email address.'},
                            status=status.HTTP_400_BAD_REQUEST)

        bookings = Booking.objects.filter(
            email_address__iexact=email,
        ).select_related('room', 'user')
        return Response({
            'searched': True,
            'email': email,
            'bookings': BookingTrackSerializer(bookings, many=True).data,
        })

    @action(detail=False, methods=['get'], url_path='room-search')
    def room_search(self, request):
        """Mirror meetspace.views.availability: free rooms for a requested slot.

        The path is `room-search` rather than `availability` only because
        `availability` is already this viewset's slot-conflict check. A missing
        date means "not searched yet" and returns the empty form, exactly as
        main's GET does; a present-but-malformed date gets main's own sentence.
        """
        if not request.query_params.get('date'):
            return Response({'searched': False, 'results': [], 'suggestions': []})

        try:
            search_date = datetime.strptime(request.query_params.get('date', ''), '%Y-%m-%d').date()
            start = datetime.strptime(request.query_params.get('start_time', ''), '%H:%M').time()
            end = datetime.strptime(request.query_params.get('end_time', ''), '%H:%M').time()
            participants = int(request.query_params.get('number_of_participants') or 0)
        except (TypeError, ValueError):
            return Response(
                {'error': 'Enter a valid date, time range and participant count.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suitable = Room.objects.filter(
            is_active=True,
            min_occupancy__lte=participants,
            max_occupancy__gte=participants,
        )
        taken = Booking.objects.filter(
            date=search_date, status=Booking.Status.APPROVED,
        ).filter(
            Q(start_time__lt=end) & Q(end_time__gt=start)
        ).values_list('room_id', flat=True)
        results = suitable.exclude(id__in=taken)

        if results.exists():
            suggestions = []
        else:
            # main's own helper, imported rather than re-implemented so the
            # 30-minute / three-day scan cannot drift from the template's.
            from meetspace.views import _time_suggestions
            suggestions = _time_suggestions(search_date, start, end, participants)

        return Response({
            'searched': True,
            'results': RoomSerializer(results, many=True).data,
            'suggestions': [
                {
                    'room': RoomSerializer(s['room']).data,
                    'date': s['date'],
                    'start_time': s['start_time'],
                    'end_time': s['end_time'],
                }
                for s in suggestions
            ],
        })


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
        # Same guard as ``ict_requisition.views.detail_view``.
        if user.is_admin() or user.is_approver():
            return qs
        return qs.filter(user=user)

    def get_permissions(self):
        if self.action in ['approve', 'decline', 'actions']:
            # ``two_stage_approve`` applies the same is_first/is_second
            # approver gates the template view does, with the same message.
            return [IsRequester()]
        return [IsRequester()]

    @action(detail=True, methods=['get'])
    def actions(self, request, pk=None):
        req = self.get_object()
        return Response(workflow.two_stage_context(request.user, req, 'ict'))

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        req = self.get_object()
        try:
            workflow.two_stage_approve(request.user, req, 'ict')
        except workflow.WorkflowError as exc:
            return Response({'error': exc.message}, status=exc.http_status)
        return Response(ICTRequisitionDetailSerializer(req).data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        serializer = ICTRequisitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = self.get_object()
        try:
            workflow.two_stage_decline(
                request.user, req, 'ict', serializer.validated_data)
        except workflow.WorkflowError as exc:
            return Response({'error': exc.message}, status=exc.http_status)
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
        # Same guard as ``internal_requisition.views.detail_view``.
        if user.is_admin() or user.is_approver():
            return qs
        return qs.filter(user=user)

    def get_permissions(self):
        if self.action in ['approve', 'decline', 'actions']:
            # ``two_stage_approve`` applies the same is_first/is_second
            # approver gates the template view does, with the same message.
            return [IsRequester()]
        return [IsRequester()]

    @action(detail=True, methods=['get'])
    def actions(self, request, pk=None):
        req = self.get_object()
        return Response(workflow.two_stage_context(request.user, req, 'internal'))

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        req = self.get_object()
        try:
            workflow.two_stage_approve(request.user, req, 'internal')
        except workflow.WorkflowError as exc:
            return Response({'error': exc.message}, status=exc.http_status)
        return Response(InternalRequisitionDetailSerializer(req).data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        serializer = InternalRequisitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = self.get_object()
        try:
            workflow.two_stage_decline(
                request.user, req, 'internal', serializer.validated_data)
        except workflow.WorkflowError as exc:
            return Response({'error': exc.message}, status=exc.http_status)
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

    CONTRACT_SORTS = {
        'id', '-id', 'pin', '-pin', 'name', '-name',
        'salary', '-salary', 'start_date', '-start_date',
    }

    def get_queryset(self):
        # Same filter set as contracts.views.contract_list: free-text search
        # across the four designation columns, a contract-type filter, the
        # Active/Expiring/Expired window, and the whitelisted sort key.
        qs = Contract.objects.all()
        params = self.request.query_params

        search = (params.get('q') or '').strip()
        if search:
            qs = qs.filter(
                Q(pin__icontains=search) |
                Q(name__icontains=search) |
                Q(designation__icontains=search) |
                Q(new_designation__icontains=search)
            )

        contract_type = params.get('type') or ''
        if contract_type:
            qs = qs.filter(contract_type=contract_type)

        status_filter = params.get('status') or ''
        today = date.today()
        if status_filter == 'Expired':
            qs = qs.filter(end_date__lt=today)
        elif status_filter == 'Expiring':
            qs = qs.filter(end_date__gte=today,
                           end_date__lte=today + timedelta(days=30))
        elif status_filter == 'Active':
            qs = qs.filter(Q(end_date__isnull=True) | Q(end_date__gte=today))

        sort_key = params.get('sort') or '-id'
        if sort_key not in self.CONTRACT_SORTS:
            sort_key = '-id'
        return qs.order_by(sort_key)

    @action(detail=False, methods=['get'], url_path='csv-template')
    def csv_template(self, request):
        """contracts.views.download_csv_template -- verbatim rows."""
        import csv as csv_mod
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename="contract_template.csv"')
        writer = csv_mod.writer(response)
        writer.writerow([
            'PIN', 'Name', 'Designation', 'Salary', 'Start Date', 'End Date',
            'Contract Type', 'Email', 'Phone', 'TIN', 'New Designation',
        ])
        writer.writerow(['123', 'John Doe', 'Senior Analyst', '50000',
                         '2025-07-01', '2026-06-30', 'Renewal',
                         'john@company.com', '01712345678', '123456789',
                         'Lead Analyst'])
        writer.writerow(['124', 'Jane Smith', 'Manager', '60000',
                         '2025-07-01', '2026-06-30', 'Extension',
                         'jane@company.com', '01723456789', '987654321', ''])
        writer.writerow(['125', 'Alex Lee', 'Analyst', '45000',
                         '2025-07-01', '2026-06-30', 'Revision',
                         'alex@company.com', '01734567890', '456789123', ''])
        return response

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, pk=None):
        """contracts.views.generate_pdf -- same template selection, same
        Content-Disposition, rendered by the same WeasyPrint call."""
        from django.http import HttpResponse

        contract = self.get_object()
        template_name = _contract_pdf_template(contract)
        html_string = render_to_string(template_name, {'contract': contract})
        try:
            payload = _render_pdf(html_string,
                                  request.build_absolute_uri('/'))
        except PdfUnavailable as exc:
            return _pdf_unavailable(exc)
        return HttpResponse(
            payload,
            content_type='application/pdf',
            headers={
                'Content-Disposition':
                    f'attachment; filename="contract_{contract.pin}.pdf"'
            },
        )

    @action(detail=True, methods=['post'], url_path='email')
    def send_email(self, request, pk=None):
        """contracts.views.send_contract_email (POST branch)."""
        contract = self.get_object()
        serializer = ContractEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subject = serializer.validated_data.get('subject') or ''
        body = serializer.validated_data.get('body') or ''
        recipient = serializer.validated_data.get('recipient') or ''

        if not recipient:
            return Response(
                {'recipient': ['Recipient email is required.']},
                status=status.HTTP_400_BAD_REQUEST)

        from django.core.mail import EmailMessage

        try:
            html_string = render_to_string(
                _contract_pdf_template(contract), {'contract': contract})
            from weasyprint import HTML
            pdf_file = HTML(
                string=html_string,
                base_url=request.build_absolute_uri('/'),
            ).write_pdf()

            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=ContractEmailConfig.get_config().default_from_email,
                to=[recipient],
            )
            email.attach(
                f'contract_{contract.pin}_{contract.id}.pdf',
                pdf_file, 'application/pdf')
            email.send()

            ContractEmailLog.objects.create(
                contract=contract,
                recipient_email=recipient,
                recipient_name=contract.name,
                subject=subject,
                status='sent',
            )
        except Exception as exc:
            ContractEmailLog.objects.create(
                contract=contract,
                recipient_email=recipient,
                recipient_name=contract.name,
                subject=subject,
                status='failed',
                error_message=str(exc),
            )
            return Response(
                {'detail': f'Failed to send email: {exc}'},
                status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {'detail': f'Email sent successfully to {recipient}!'})

    @action(detail=False, methods=['post'], url_path='bulk')
    def bulk(self, request):
        """contracts.views.bulk_create_contracts (POST branch)."""
        import csv as csv_mod
        from datetime import datetime as _dt

        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': 'No file uploaded!'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not upload.name.endswith('.csv'):
            return Response({'detail': 'Only CSV files allowed!'},
                            status=status.HTTP_400_BAD_REQUEST)

        def parse_date(value):
            if not value:
                return None
            try:
                return _dt.strptime(value.strip(), '%Y-%m-%d').date()
            except Exception:
                return None

        created = failed = updated = 0
        try:
            decoded = upload.read().decode('utf-8-sig').splitlines()
            reader = csv_mod.DictReader(decoded)
            if reader.fieldnames:
                reader.fieldnames = [h.strip() for h in reader.fieldnames]

            for row in reader:
                try:
                    row = {k.strip(): (v.strip() if v else '')
                           for k, v in row.items()}

                    pin = row.get('PIN')
                    name = row.get('Name')
                    designation = row.get('Designation')
                    salary = float(row.get('Salary') or 0)
                    start_date = parse_date(row.get('Start Date'))
                    end_date = parse_date(row.get('End Date'))
                    contract_type = row.get('Contract Type') or 'New'
                    new_designation = row.get('New Designation') or None

                    if not pin:
                        failed += 1
                        continue

                    employee, is_new = Employee.objects.get_or_create(pin=pin)
                    if name:
                        employee.name = name
                    if designation:
                        employee.designation = designation
                    if salary:
                        employee.salary = salary
                    if row.get('Email'):
                        employee.email = row.get('Email')
                    if row.get('Phone'):
                        employee.phone = row.get('Phone')
                    if row.get('TIN'):
                        employee.tin = row.get('TIN')
                    employee.save()

                    if not is_new:
                        updated += 1

                    Contract.objects.create(
                        pin=pin,
                        name=employee.name,
                        designation=designation or employee.designation,
                        salary=salary or employee.salary,
                        start_date=start_date,
                        end_date=end_date,
                        contract_type=contract_type,
                        new_designation=(
                            new_designation
                            if contract_type == 'Renewal' else None),
                    )
                    created += 1
                except Exception:
                    failed += 1
        except Exception as exc:
            return Response({'detail': f'Upload failed: {exc}'},
                            status=status.HTTP_400_BAD_REQUEST)

        detail = f'{created} contracts created successfully!'
        if updated:
            detail += f' {updated} employees updated.'
        return Response({
            'detail': detail,
            'warning': f'{failed} rows failed!' if failed else '',
            'created': created,
            'updated': updated,
            'failed': failed,
        })

    @action(detail=False, methods=['post'], url_path='bulk-email')
    def bulk_email(self, request):
        """contracts.views.bulk_email_contracts -- queue one django-q task per
        selected contract, all in the same group so the status page can count
        them."""
        import time

        serializer = ContractBulkEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contract_ids = serializer.validated_data['contract_ids']
        subject = serializer.validated_data.get('subject') or 'Contract Document'
        body = serializer.validated_data.get('body') or ''

        base_url = request.build_absolute_uri('/')
        group_name = f"bulk_email_{request.user.id}_{int(time.time())}"

        from django_q.tasks import async_task
        for contract_id in contract_ids:
            async_task(
                'contracts.tasks.send_contract_email_task',
                contract_id, subject, body, base_url, group_name,
                group=group_name,
            )

        return Response({
            'group': group_name,
            'total': len(contract_ids),
            'started': time.time(),
        })

    @action(detail=False, methods=['get'], url_path='bulk-email-status')
    def bulk_email_status(self, request):
        """contracts.views.bulk_email_status, minus the session: the React
        caller passes the group it was handed by POST /bulk-email/."""
        import time

        from django_q.models import Success, Failure

        group = request.query_params.get('group') or ''
        total = int(request.query_params.get('total') or 0)
        started = float(
            request.query_params.get('started') or time.time())

        sent = failed = 0
        pending = total
        results = []

        if group and total > 0:
            success_qs = Success.objects.filter(group=group)
            failure_qs = Failure.objects.filter(group=group)
            sent = success_qs.count()
            failed = failure_qs.count()
            pending = total - sent - failed

            for s in success_qs.all()[:50]:
                result = s.result if isinstance(s.result, dict) else {}
                results.append({
                    'contract_id': result.get('contract_id', '?'),
                    'name': result.get('name', ''),
                    'email': result.get('email', ''),
                    'status': 'sent',
                })
            for f in failure_qs.all()[:10]:
                result = f.result if isinstance(f.result, dict) else {}
                results.append({
                    'contract_id': result.get('contract_id', '?'),
                    'name': result.get('name', ''),
                    'email': result.get('email', ''),
                    'status': 'failed',
                    'reason': result.get('reason', str(f.result)[:200]),
                })

        return Response({
            'total': total,
            'sent': sent,
            'failed': failed,
            'pending': max(pending, 0),
            'finished': pending <= 0,
            'results': results,
            'elapsed': round(time.time() - started, 1),
            'group': group,
        })

    @action(detail=True, methods=['get'], url_path='defaults')
    def email_defaults(self, request, pk=None):
        """The subject/body contracts.views.send_contract_email pre-fills on
        GET, plus the employee email it looks up."""
        contract = self.get_object()
        defaults = _contract_email_defaults(contract)

        employee_email = ''
        employee = Employee.objects.filter(pin=contract.pin).first()
        if employee and employee.email:
            employee_email = employee.email

        return Response({
            'subject': defaults['subject'],
            'body': defaults['body'],
            'employee_email': employee_email,
        })

    @action(detail=False, methods=['get'], url_path='email-log')
    def email_log(self, request):
        """contracts.views.email_log -- contracts' own EmailLog table, most
        recent 200. Deliberately not `/api/email-logs/`, which reads the
        notifications app's table behind the portal sidebar."""
        logs = list(ContractEmailLog.objects.all()[:200])
        return Response({
            'count': len(logs),
            'results': ContractEmailLogSerializer(logs, many=True).data,
        })

    @action(detail=False, methods=['get', 'post'], url_path='email-config')
    def email_config(self, request):
        """contracts.views.email_settings.

        `action=save` persists the six fields; `action=test` fills the config
        in memory, tries the SMTP handshake and reports, without saving --
        exactly what the template's two branches do.
        """
        config = ContractEmailConfig.get_config()

        if request.method == 'GET':
            return Response(ContractEmailConfigSerializer(config).data)

        fields = {
            'email_host': (str(request.data.get('email_host', '')).strip(),
                           True),
            'email_host_user': (
                str(request.data.get('email_host_user', '')).strip(), True),
            'email_host_password': (
                str(request.data.get('email_host_password', '')).strip(),
                True),
            'default_from_email': (
                str(request.data.get('default_from_email', '')).strip(), True),
        }
        for name, (value, _) in fields.items():
            setattr(config, name, value)
        try:
            config.email_port = int(request.data.get('email_port', 587))
        except (TypeError, ValueError):
            config.email_port = 587
        config.email_use_tls = request.data.get('email_use_tls') in (
            True, 'true', 'on', '1', 1)

        action = request.data.get('action', 'save')

        if action == 'test':
            import smtplib
            try:
                server = smtplib.SMTP(
                    config.email_host, config.email_port, timeout=10)
                if config.email_use_tls:
                    server.starttls()
                server.login(config.email_host_user,
                             config.email_host_password)
                server.quit()
                return Response({
                    'detail': 'Connection successful! SMTP server is reachable.',
                    'level': 'success',
                    'config': ContractEmailConfigSerializer(config).data,
                })
            except Exception as exc:
                return Response(
                    {
                        'detail': f'Connection failed: {exc}',
                        'level': 'error',
                        'config': ContractEmailConfigSerializer(config).data,
                    },
                    status=status.HTTP_400_BAD_REQUEST)

        config.save()
        return Response({
            'detail': 'Email settings saved successfully!',
            'level': 'success',
            'config': ContractEmailConfigSerializer(config).data,
        })


class PdfUnavailable(Exception):
    """WeasyPrint could not be imported or could not reach its native libs.

    WeasyPrint is listed in ``requirements.txt`` (the Linux deploy) but is
    deliberately absent from ``requirements-windows.txt``: it loads Pango /
    GObject / Cairo through ctypes, which Windows does not ship. ``main`` has
    the very same hole -- ``generate_payslip_pdf`` and ``generate_pdf`` 500
    here -- so rather than surfacing a raw traceback the API says so plainly.
    """


def _render_pdf(html_string, base_url):
    """``weasyprint.HTML(...).write_pdf()`` with a host-capability guard."""
    try:
        from weasyprint import HTML
    except (ImportError, OSError) as exc:  # missing module or missing DLLs
        raise PdfUnavailable(str(exc)) from exc
    try:
        return HTML(string=html_string, base_url=base_url).write_pdf()
    except (ImportError, OSError) as exc:
        raise PdfUnavailable(str(exc)) from exc


def _pdf_unavailable(exc):
    return Response(
        {
            'detail': (
                'PDF export is unavailable on this host: WeasyPrint needs the '
                'Pango/GObject system libraries, which are not installed '
                f'(requirements-windows.txt omits weasyprint). ({exc})'
            ),
            'code': 'pdf_unavailable',
        },
        status=status.HTTP_501_NOT_IMPLEMENTED,
    )


def _contract_pdf_template(contract):
    """contracts.views.generate_pdf's template pick, verbatim."""
    return {
        'Renewal': 'contracts/pdf/renewal.html',
        'Extension': 'contracts/pdf/extension.html',
        'Revision': 'contracts/pdf/revision.html',
        'New': 'contracts/pdf/new.html',
    }.get(contract.contract_type, 'contracts/pdf/new.html')


def _contract_email_defaults(contract):
    """contracts.views.send_contract_email's GET pre-fill, verbatim."""
    if contract.contract_type == 'Extension':
        return {
            'subject': 'Extension of contract letter',
            'body': (
                f"Dear {contract.name},\n\n"
                "I hope this email finds you well. Please find your "
                "extension of contract letter attached with this email.\n\n"
                "You are requested to preserve a copy of the letter with "
                "yourself and send a copy to us via email with your "
                "signature in the letter.\n\n"
                "Please let us know if any further information is required."
            ),
        }
    if contract.contract_type == 'Renewal':
        return {
            'subject': 'Renewal of contract',
            'body': (
                f"Please find attached the renewal contract for "
                f"{contract.name} (PIN: {contract.pin}).\n\n"
                f"Contract Period: {contract.start_date} to "
                f"{contract.end_date}\n\nBest regards,\nHR Department"
            ),
        }
    if contract.contract_type == 'New':
        return {
            'subject': 'New Contract',
            'body': (
                f"Please find attached the new contract for "
                f"{contract.name} (PIN: {contract.pin}).\n\n"
                f"Contract Period: {contract.start_date} to "
                f"{contract.end_date}\n\nBest regards,\nHR Department"
            ),
        }
    if contract.contract_type == 'Revision':
        return {
            'subject': 'Revision of contract',
            'body': (
                f"Please find attached the revised contract for "
                f"{contract.name} (PIN: {contract.pin}).\n\n"
                f"Contract Period: {contract.start_date} to "
                f"{contract.end_date}\n\nBest regards,\nHR Department"
            ),
        }
    return {
        'subject': 'Contract Document',
        'body': f"Please find attached the contract for {contract.name}.",
    }


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
    # Every route in employees/urls.py addresses an employee by PIN
    # (`edit/<pin>/`, `detail/<pin>/`, `api/<pin>/`), never by the numeric pk.
    lookup_field = 'pin'

    def get_queryset(self):
        # employees.views.employee_list pins the order to `pin`.
        return Employee.objects.all().order_by('pin')

    def perform_destroy(self, instance):
        # employees.views.delete_employee also clears the contract history
        # hanging off the same PIN before removing the row.
        Contract.objects.filter(pin=instance.pin).delete()
        instance.delete()

    @action(detail=False, methods=['post'], url_path='import')
    def import_csv(self, request):
        """employees.views.import_employees (POST branch) -- positional CSV,
        header row skipped, update_or_create keyed on PIN."""
        import csv as csv_mod

        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': 'No file uploaded!'},
                            status=status.HTTP_400_BAD_REQUEST)

        created = failed = 0
        try:
            decoded = upload.read().decode('utf-8')
            reader = csv_mod.reader(decoded.splitlines())
            next(reader, None)

            for row in reader:
                if len(row) < 2:
                    continue
                try:
                    pin = row[0].strip()
                    name = row[1].strip()
                    Employee.objects.update_or_create(
                        pin=pin,
                        defaults={
                            'name': name,
                            'designation': (
                                row[2].strip() if len(row) > 2 else 'Staff'),
                            'gender': row[3].strip() if len(row) > 3 else '',
                            'tin': row[4].strip() if len(row) > 4 else '',
                            'phone': row[5].strip() if len(row) > 5 else '',
                            'email': row[6].strip() if len(row) > 6 else '',
                            'salary': (
                                row[7].strip() if len(row) > 7 else 0),
                        },
                    )
                    created += 1
                except Exception:
                    failed += 1
        except Exception as exc:
            return Response({'detail': f'Error: {exc}'},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'detail': f'{created} employees imported!',
            'warning': f'{failed} rows failed' if failed else '',
            'created': created,
            'failed': failed,
        })

    @action(detail=False, methods=['get'], url_path='lookup')
    def lookup(self, request):
        """employees.views.employee_api -- the contract form's PIN autofill."""
        pin = (request.query_params.get('pin') or '').strip()
        if not pin:
            return Response({'exists': False})
        try:
            emp = Employee.objects.get(pin=pin)
        except Employee.DoesNotExist:
            return Response({'exists': False})
        return Response({
            'exists': True,
            'name': emp.name,
            'designation': emp.designation,
            'salary': float(emp.salary) if emp.salary else 0,
            'phone': emp.phone or '',
            'email': emp.email or '',
            'tin': emp.tin or '',
        })


# Payslip ViewSets
class PayslipViewSet(viewsets.ModelViewSet):
    # Payslip has no relations at all -- it is a flat row keyed by PIN.
    queryset = Payslip.objects.all()
    serializer_class = PayslipSerializer
    permission_classes = [IsHRAdmin | IsAdminUser]

    def get_queryset(self):
        # payslip.views.payslip_list orders newest-first.
        return Payslip.objects.all().order_by('-id')

    def get_serializer_class(self):
        # POST/PUT re-runs the 50/30/10/10 split the form does; the list and
        # detail read back the already-split columns through the plain model
        # serializer.
        if self.action in ('create', 'update', 'partial_update'):
            return PayslipCreateSerializer
        return PayslipSerializer

    @action(detail=False, methods=['post'], url_path='bulk')
    def bulk(self, request):
        """payslip.bulk_upload_views.bulk_upload_payslip (POST branch).

        One CSV row = one employee: PIN, gender, TIN, then twelve monthly
        totals. Existing payslips for that PIN/year are wiped first, and every
        non-zero month is written as a 50/30/10/10 split.
        """
        import csv as csv_mod

        year = request.data.get('year', '2025')
        upload = request.FILES.get('file')
        if not upload:
            return Response(
                {'detail': 'No file uploaded! Please select a CSV file.'},
                status=status.HTTP_400_BAD_REQUEST)

        months = ["July", "August", "September", "October", "November",
                  "December", "January", "February", "March", "April",
                  "May", "June"]

        created = failed = 0
        error_details = []
        try:
            decoded = upload.read().decode('utf-8')
            reader = csv_mod.reader(decoded.splitlines())
            next(reader, None)  # Skip header

            pin_mapping = {}
            employee_file = request.FILES.get('employee_file')
            if employee_file:
                emp_data = employee_file.read().decode('utf-8')
                emp_reader = csv_mod.reader(emp_data.splitlines())
                next(emp_reader, None)
                for emp_row in emp_reader:
                    if len(emp_row) >= 4:
                        pin_mapping[emp_row[0].strip()] = {
                            'real_pin': emp_row[1].strip(),
                            'name': emp_row[2].strip(),
                            'designation': (
                                emp_row[3].strip()
                                if len(emp_row) > 3 else 'Staff'),
                        }

            for row_idx, row in enumerate(reader, start=2):
                if len(row) < 4:
                    failed += 1
                    error_details.append(
                        f"Row {row_idx}: Insufficient columns "
                        f"(need at least 4, got {len(row)})")
                    continue
                try:
                    dummy_pin = row[0].strip()
                    gender = row[1].strip() if len(row) > 1 else ''
                    tin = row[2].strip() if len(row) > 2 else ''

                    emp_info = pin_mapping.get(dummy_pin, {})
                    real_pin = emp_info.get('real_pin', dummy_pin)
                    name = emp_info.get('name', f"Employee {real_pin}")
                    designation = emp_info.get('designation', 'Staff')

                    values = []
                    for i in range(3, 15):
                        raw = (row[i].replace(',', '').replace('BDT', '').strip()
                               if i < len(row) else '0')
                        try:
                            values.append(int(float(raw)))
                        except Exception:
                            values.append(0)

                    Payslip.objects.filter(pin=real_pin, year=year).delete()

                    for idx, m in enumerate(months):
                        total = values[idx]
                        if total > 0:
                            Payslip.objects.create(
                                pin=real_pin, name=name,
                                designation=designation,
                                gender=gender, tin=tin, month=m, year=year,
                                basic_salary=total * 0.50,
                                house_rent=total * 0.30,
                                medical_allowance=total * 0.10,
                                conveyance=total * 0.10,
                            )
                            created += 1
                except Exception as exc:
                    failed += 1
                    error_details.append(f"Row {row_idx}: {exc}")
        except Exception as exc:
            return Response({'detail': f"❌ Upload failed: {exc}"},
                            status=status.HTTP_400_BAD_REQUEST)

        detail = ''
        if created > 0:
            detail = (f"✅ {created} payslips uploaded successfully "
                      f"for year {year}!")
        warning = ''
        if failed > 0:
            warning = f"⚠️ {failed} rows failed. "
            if error_details:
                warning += ("First 3 errors: "
                            + "; ".join(error_details[:3]))

        return Response({
            'detail': detail,
            'warning': warning,
            'created': created,
            'failed': failed,
            'errors': error_details[:10],
        })

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, pk=None):
        """payslip.views.generate_payslip_pdf."""
        from django.http import HttpResponse

        payslip = self.get_object()
        html_string = render_to_string(
            'payslip/pdf/payslip.html', {'payslip': payslip})
        try:
            payload = _render_pdf(html_string,
                                  request.build_absolute_uri('/'))
        except PdfUnavailable as exc:
            return _pdf_unavailable(exc)
        filename = (
            f'payslip_{payslip.pin}_{payslip.month}_{payslip.year}.pdf')
        return HttpResponse(
            payload,
            content_type='application/pdf',
            headers={'Content-Disposition':
                     f'attachment; filename="{filename}"'},
        )


class PayslipRequestViewSet(viewsets.ModelViewSet):
    # PayslipRequest is also relation-free (name / pin / months / year).
    queryset = PayslipRequest.objects.all()
    serializer_class = PayslipRequestSerializer

    def get_queryset(self):
        # payslip.views.payslip_requests orders newest-first.
        return PayslipRequest.objects.all().order_by('-created_at')

    def get_permissions(self):
        # payslip.views.request_payslip is a public form (no @login_required);
        # payslip.views.payslip_requests is HR-admin only. Everything else
        # (retrieval, edits, deletes) stays behind a signed-in user.
        if self.action == 'create':
            return [permissions.AllowAny()]
        if self.action in ('list', 'retrieve', 'update',
                           'partial_update', 'destroy'):
            # `get_permissions` is what DRF calls *instead of* the default
            # list, so the operands have to be built into instances here --
            # returning the holder or the class itself leaves DRF holding
            # something with no `has_permission`.
            return [(IsHRAdmin | IsAdminUser)()]
        return [IsRequester()]


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
                'bookings': Booking.objects.filter(user=user).count(),
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
    from portal_config.models import FieldType, StageAction

    return Response({
        'roles': [{'value': v, 'label': l} for v, l in User.Role.choices],
        'stage_actions': [{'value': a.value, 'label': a.label} for a in StageAction],
        'departments': [{'value': v, 'label': l} for v, l in Department.choices],
        # field_list.html renders these straight off `FieldType.choices`, so the
        # Form Builder needs them from the same source rather than a copy.
        'field_types': [{'value': v, 'label': l} for v, l in FieldType.choices],
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

# =============================================================================
# Tier 3 -- documentation, self-registration and notification deep links
# =============================================================================


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def signup(request):
    """``accounts.views.signup`` -- self-registration that creates a *disabled*
    account, so an administrator still has to approve it from User Management.

    main reads ``request.POST['username']`` straight out of the dict and 500s
    when it is missing; here the same two sentences it can actually produce
    ("Passwords do not match", "Username already exists") come back as 400s, plus
    a guard for the empty-username case main never reaches from its own form.
    """
    username = request.data.get('username') or ''
    password1 = request.data.get('password1') or ''
    password2 = request.data.get('password2') or ''
    email = request.data.get('email') or ''
    phone = request.data.get('phone') or ''
    role = request.data.get('role') or User.Role.REQUESTER

    if not username:
        return Response({'error': 'Username is required.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if password1 != password2:
        return Response({'error': 'Passwords do not match'},
                        status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'},
                        status=status.HTTP_400_BAD_REQUEST)

    User.objects.create_user(
        username=username,
        password=password1,
        email=email,
        phone=phone,
        role=role,
        is_active=False,
    )
    return Response({'detail': 'Account created.'})


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def documentation(request):
    """``requisition_portal.views.documentation`` -- the same rendered page and
    the same two download formats.

    ``?download=html`` streams back exactly what main's view streams (an
    attachment), so the file that lands on disk is identical. ``?download=pdf``
    keeps main's own sentence about WeasyPrint being unavailable -- it answers
    JSON rather than main's plain-text body so the React page can show the
    sentence instead of downloading a broken file. The React Download button
    points at ``?download=html``; main's button points at ``?download=1``,
    which its own view ignores, so there it just reloads the page.
    """
    from django.http import HttpResponse

    fmt = request.query_params.get('download')
    html = render_to_string('documentation.html') if fmt in ('html', 'pdf') else None

    if fmt == 'html':
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = \
            'attachment; filename="Requisition_Portal_Documentation.html"'
        return response

    if fmt == 'pdf':
        try:
            pdf = _render_pdf(html, base_url=None)
        except PdfUnavailable:
            return Response(
                {
                    'detail': (
                        'PDF generation requires weasyprint which is not '
                        'installed. On Windows, install it via WSL2 or use '
                        'the HTML download option.'
                    ),
                    'code': 'pdf_unavailable',
                },
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = \
            'attachment; filename="Requisition_Portal_Documentation.pdf"'
        return response

    return Response({'html': render_to_string('documentation.html')})


def _resolve_action(request, token):
    """Turn a signed email link into the state its page should show.

    ``notifications.views.email_action_view`` renders one of three templates
    (action_error / reject_reason / action_success) or redirects to login, and
    applies an approval on the GET that opens the link. This returns the same
    choice as data and mutates nothing, so the React page can draw exactly the
    card main would have rendered while a reload can never apply an approval
    twice -- ``POST`` re-resolves and only then acts.

    Returns ``(http_status, payload)``.
    """
    from portal_config import engine
    from notifications.utils import unsign_action_token
    from notifications.views import get_requisition_model

    def error(message):
        return status.HTTP_200_OK, {'kind': 'error', 'error': message}

    data = unsign_action_token(token)
    if not data:
        return error('Invalid or expired link.')

    model = get_requisition_model(data['type'])
    if not model:
        return error('Invalid requisition type.')

    # main looks both rows up with get_object_or_404, and does so *before* the
    # login check, so a stale id still 404s for a signed-out visitor.
    try:
        requisition = model.objects.get(pk=data['id'])
    except model.DoesNotExist:
        return status.HTTP_404_NOT_FOUND, {'kind': 'error', 'error': 'Not found.'}
    try:
        actor = User.objects.get(pk=data['user_id'])
    except User.DoesNotExist:
        return status.HTTP_404_NOT_FOUND, {'kind': 'error', 'error': 'Not found.'}

    if not request.user.is_authenticated:
        # main redirects to LOGIN_URL?next=...; the React page turns this into
        # the same jump, back to its own path for the same token. Answered with
        # a 200 and a `kind` rather than a 401 so the axios refresh interceptor
        # does not hijack the response before the page can read it.
        return status.HTTP_200_OK, {
            'kind': 'login_required',
            'next': f'/notifications/action/{token}',
        }
    if request.user.pk != actor.pk:
        return error(
            'This approval link was sent to a different user. '
            'Sign in as that user, or open the requisition from your dashboard.'
        )

    stage = engine.get_stage(data['type'], requisition.status)
    if stage is None or stage.is_terminal:
        return error('This requisition is no longer awaiting approval.')
    if not engine.stage_allows(stage, actor):
        return error(f'You are not authorised to act at "{stage.name}".')

    base = {
        'action': data['action'],
        'req_type': data['type'],
        'requisition': {
            'id': requisition.pk,
            'request_number': requisition.request_number,
        },
        'stage': {'key': stage.key, 'name': stage.name},
        'portal_url': '/',
        'token': token,
    }

    if data['action'] == 'approve':
        if not stage.can_approve:
            return error(f'"{stage.name}" does not allow approval.')
        return status.HTTP_200_OK, {
            **base,
            'kind': 'approve-ready',
            'message': f'Requisition #{requisition.pk} approved at "{stage.name}".',
        }

    if data['action'] == 'reject':
        if not stage.can_decline:
            return error(f'"{stage.name}" does not allow declining.')
        return status.HTTP_200_OK, {
            **base,
            'kind': 'reject-form',
            'message': f'Requisition #{requisition.pk} rejected at "{stage.name}".',
            'require_reason': bool(stage.require_reason_on_decline),
        }

    return error('Invalid action.')


@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
def notification_action(request, token):
    """``notifications.views.email_action_view`` -- approve or decline from the
    link in an approval email.

    GET only resolves (see ``_resolve_action``); the React page issues POST
    once, which re-resolves and then performs the same work main's handler does
    -- audit entry, move to the next configured stage, mail the next approver
    and the requester.
    """
    http_status, payload = _resolve_action(request, token)

    if http_status != status.HTTP_200_OK:
        return Response(payload, status=http_status)

    if request.method == 'GET':
        return Response(payload)

    # `login_required` and every `error` resolve to a card with nothing to do --
    # the page still POSTs so a stale link reports exactly what it would have
    # rendered, rather than applying against a state that has since moved on.
    if payload['kind'] not in ('approve-ready', 'reject-form'):
        return Response(payload)

    # ---- perform ----
    from portal_config import engine
    from notifications.utils import unsign_action_token, log_audit, notify_requester
    from notifications.views import _advance_from_email, get_requisition_model

    data = unsign_action_token(token)
    model = get_requisition_model(data['type'])
    requisition = model.objects.get(pk=data['id'])
    actor = User.objects.get(pk=data['user_id'])
    stage = engine.get_stage(data['type'], requisition.status)

    if payload['action'] == 'approve':
        _advance_from_email(request, data['type'], requisition, stage, actor)
        return Response({'kind': 'success', 'message': payload['message']})

    # reject
    reason = (request.data.get('reason') or '').strip()
    if not reason and payload.get('require_reason'):
        return Response(
            {'detail': 'Please give a reason so the requester knows what to fix.',
             'kind': 'validation'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    requisition.status = model.Status.REJECTED
    requisition.rejection_reason = reason
    requisition.rejected_at = timezone.now()
    requisition.save()

    log_audit(data['type'], requisition.pk, requisition.request_number,
              'rejected', actor, f'{stage.name}: {reason}')
    notify_requester(data['type'], requisition, data['type'], 'rejected')
    return Response({'kind': 'success', 'message': payload['message']})


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def notification_track(request, req_type, pk):
    """``notifications.views.track_view`` -- the public status card the
    "Track Request Status" button in the requester's email opens.

    ``track.html`` is a standalone page (no base.html), so this returns the
    requisition and its label and the React route draws the same card.
    """
    from notifications.views import get_requisition_model

    model = get_requisition_model(req_type)
    if not model:
        return Response({'error': 'Invalid requisition type.'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        requisition = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    labels = {'ict': 'ICT', 'transport': 'Transport', 'internal': 'Internal'}
    return Response({
        'label': labels.get(req_type, 'Requisitions'),
        'r': NotificationTrackSerializer(requisition).data,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser | IsICTAdmin | IsTransportAdmin | IsInternalAdmin])
def notification_send_reminder(request, req_type, pk):
    """``notifications.views.send_reminder`` -- re-send the approval request to
    whoever owns the stage the requisition is sitting at.

    main guards the same four roles (admin, or the module's own admin) and then
    redirects back with a message; here the guard is the DRF permission and the
    two messages come back as data. Both methods are accepted because main
    exposes it as a plain link while React presses it from a button.
    """
    from notifications.views import _get_req_model
    from notifications.utils import send_approval_request
    from portal_config import engine

    model = _get_req_model(req_type)
    if not model:
        return Response({'detail': 'Invalid requisition type.', 'level': 'error'},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        requisition = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    stage = engine.get_stage(req_type, requisition.status)
    if stage is None or stage.is_terminal:
        return Response({
            'detail': f'Requisition #{requisition.pk} is not pending approval.',
            'level': 'info',
        })

    send_approval_request(req_type, requisition, req_type, requisition.status)
    return Response({
        'detail': f'Approval request sent to {stage.name} for #{requisition.pk}.',
        'level': 'success',
    })
