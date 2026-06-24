from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    path('', views.contracts_dashboard, name='dashboard'),
    path('create/', views.create_contract, name='create_contract'),
    path('list/', views.contract_list, name='contract_list'),
    path('pdf/<int:id>/', views.generate_pdf, name='generate_pdf'),
    path('contracts/delete/<int:id>/', views.delete_contract, name='delete_contract'),
    path('contracts/', views.contracts_dashboard, name='contracts_dashboard'),
    path('dashboard/', views.contracts_dashboard, name='contracts_dashboard'),
    path('bulk-create/', views.bulk_create_contracts, name='bulk_upload_contracts'),
    path('contracts/bulk-upload/', views.bulk_create_contracts, name='bulk_upload_contracts'),
    path('email/<int:id>/', views.send_contract_email, name='send_contract_email'),
    path('bulk-email/', views.bulk_email_contracts, name='bulk_email_contracts'),
    path('bulk-email-status/', views.bulk_email_status, name='bulk_email_status'),
    path('download-csv-template/', views.download_csv_template, name='download_csv_template'),
    path('manual/', views.system_manual, name='system_manual'),
    path('email-log/', views.email_log, name='email_log'),
    path('email-settings/', views.email_settings, name='email_settings'),
]