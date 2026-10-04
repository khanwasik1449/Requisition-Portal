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
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'drivers', DriverViewSet, basename='driver')
router.register(r'transport', TransportRequisitionViewSet, basename='transport')
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'bookings', BookingViewSet, basename='booking')
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

    # Public endpoints
    path('public/modules/', public_modules, name='public-modules'),
    path('public/modules/<str:module_key>/fields/', module_form_fields, name='public-module-fields'),
    path('public/modules/<str:module_key>/workflow/', module_workflow, name='public-module-workflow'),

    # Router
    path('', include(router.urls)),
]