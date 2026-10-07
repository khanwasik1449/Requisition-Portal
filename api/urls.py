from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView, CustomTokenRefreshView, LogoutView, MeView,
    ChangePasswordView, RegisterView,
    UserViewSet,
    VehicleViewSet, DriverViewSet, TransportRequisitionViewSet,
    RoomViewSet, BookingViewSet, AnnouncementViewSet,
    ICTRequisitionViewSet, InternalRequisitionViewSet,
    ContractViewSet, EmailConfigViewSet, EmailLogViewSet,
    EmployeeViewSet, PayslipViewSet, PayslipRequestViewSet,
    ModuleViewSet, FormFieldViewSet, WorkflowStageViewSet,
    AuditLogViewSet, NotificationEmailLogViewSet,
    dashboard_stats, public_modules, module_form_fields, module_workflow,
    transport_track, transport_history, transport_report, transport_report_export,
    my_requisitions, portal_choices,
    signup, documentation, notification_action, notification_track,
    notification_send_reminder,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'drivers', DriverViewSet, basename='driver')
router.register(r'transport', TransportRequisitionViewSet, basename='transport')
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'bookings', BookingViewSet, basename='booking')
# The React pages address bookings under the app's own namespace
# (`/meetspace/`, matching Django's `meetspace:` urls), while the router's
# resource name is `bookings`. Register both so either path resolves.
router.register(r'meetspace', BookingViewSet, basename='meetspace')
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'ict', ICTRequisitionViewSet, basename='ict')
router.register(r'internal', InternalRequisitionViewSet, basename='internal')
router.register(r'contracts', ContractViewSet, basename='contract')
router.register(r'email-configs', EmailConfigViewSet, basename='email-config')
router.register(r'email-logs', EmailLogViewSet, basename='email-log')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'payslips', PayslipViewSet, basename='payslip')
router.register(r'payslip-requests', PayslipRequestViewSet, basename='payslip-request')
router.register(r'modules', ModuleViewSet, basename='module')
router.register(r'form-fields', FormFieldViewSet, basename='form-field')
router.register(r'workflow-stages', WorkflowStageViewSet, basename='workflow-stage')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
router.register(r'notification-email-logs', NotificationEmailLogViewSet, basename='notification-email-log')

urlpatterns = [
    # Auth
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('auth/register/', RegisterView.as_view(), name='register'),

    # Dashboard
    path('dashboard/stats/', dashboard_stats, name='dashboard-stats'),
    path('my-requisitions/', my_requisitions, name='my-requisitions'),
    path('portal-choices/', portal_choices, name='portal-choices'),

    # Public endpoints
    path('public/modules/', public_modules, name='public-modules'),
    path('public/modules/<str:module_key>/fields/', module_form_fields, name='public-module-fields'),
    path('public/modules/<str:module_key>/workflow/', module_workflow, name='public-module-workflow'),
    # Registered before the router: `transport/track/` would otherwise be
    # swallowed by the router's `transport/<pk>/` detail pattern. Same for
    # `history/` and `report/`, which would be read as a pk of "history".
    path('transport/track/', transport_track, name='transport-track'),
    path('transport/history/', transport_history, name='transport-history'),
    path('transport/report/', transport_report, name='transport-report'),
    path('transport/report/export/', transport_report_export, name='transport-report-export'),

    # Tier 3 -- documentation, self-registration and notification deep links.
    # Registered before the router for the same reason as the block above: a
    # bare `notifications/<x>/` would otherwise be read as a router lookup.
    path('auth/signup/', signup, name='signup'),
    path('documentation/', documentation, name='documentation'),
    path('notifications/action/<str:token>/', notification_action, name='notification-action'),
    path('notifications/track/<str:req_type>/<int:pk>/', notification_track, name='notification-track'),
    path('notifications/send-reminder/<str:req_type>/<int:pk>/',
         notification_send_reminder, name='notification-send-reminder'),

    # Router
    path('', include(router.urls)),
]