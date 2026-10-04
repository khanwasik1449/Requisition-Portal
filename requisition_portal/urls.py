from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from portal_config.engine import enabled_module_keys
from portal_config.routing import module_include

from . import views

# Django admin branding — matches the portal name used across the UI.
admin.site.site_header = 'BRAC IED Central Portal'
admin.site.site_title = 'BRAC IED Central Portal'
admin.site.index_title = 'Administration'

urlpatterns = [
    path('admin/', admin.site.urls),
    # API endpoints
    path('api/', include('api.urls')),
    # API Schema (OpenAPI)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('my-requisitions/', views.my_requisitions, name='my_requisitions'),
    path('documentation/', views.documentation, name='documentation'),
    path('accounts/', include('accounts.urls')),
    path('notifications/', include('notifications.urls')),
    path('portal-config/', include('portal_config.urls')),
]

# Feature-flagged modules.
#
# Every module is always present in the URL conf; whether it resolves is
# decided per request by ModuleURLResolver, which reads the module's
# is_enabled flag from the database. That keeps the on/off switch in the Form
# Builder live without a worker restart. A disabled module raises Resolver404,
# so its URLs 404 and its named URLs cannot be reversed from a template.
_MODULES = [
    ('ict', 'ict/', 'ict_requisition.urls'),
    ('transport', 'transport/', 'transport_requisition.urls'),
    ('internal', 'internal/', 'internal_requisition.urls'),
    ('meetspace', 'meetspace/', 'meetspace.urls'),
]

for _key, _prefix, _module in _MODULES:
    urlpatterns.append(module_include(_key, _prefix, _module))

# HR is a group of three apps rather than one, so each is wrapped separately
# but all gated on the same 'hr' module flag.
urlpatterns += [
    module_include('hr', 'hr/contracts/', 'contracts.urls'),
    module_include('hr', 'hr/employees/', 'employees.urls'),
    module_include('hr', 'hr/payslip/', 'payslip.urls'),
]
