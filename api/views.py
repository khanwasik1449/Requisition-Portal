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
from datetime import date, datetime, timedelta

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
    BookingCreateSerializer, BookingActionSerializer, BookingTrackSerializer,
    AnnouncementSerializer,
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
from . import workflow


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