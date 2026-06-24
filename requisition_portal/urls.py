from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('my-requisitions/', views.my_requisitions, name='my_requisitions'),
    path('documentation/', views.documentation, name='documentation'),
    path('accounts/', include('accounts.urls')),
    path('ict/', include('ict_requisition.urls')),
    path('transport/', include('transport_requisition.urls')),
    path('internal/', include('internal_requisition.urls')),
    path('notifications/', include('notifications.urls')),
    path('hr/contracts/', include('contracts.urls')),
    path('hr/employees/', include('employees.urls')),
    path('hr/payslip/', include('payslip.urls')),
]
