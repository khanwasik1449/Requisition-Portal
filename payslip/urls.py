from django.urls import path
from . import views
from . import bulk_upload_views

app_name = 'payslip'

urlpatterns = [
    path('', views.create_payslip, name='create_payslip'),
    path('list/', views.payslip_list, name='payslip_list'),
    path('pdf/<int:id>/', views.generate_payslip_pdf, name='generate_payslip_pdf'),
    path('bulk/', bulk_upload_views.bulk_upload_payslip, name='bulk_upload_payslip'),
    path('request/', views.request_payslip, name='request_payslip'),
    path('requests/', views.payslip_requests, name='payslip_requests'),
]