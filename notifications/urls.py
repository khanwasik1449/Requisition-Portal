from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('email-config/', views.config_list, name='config_list'),
    path('email-config/create/', views.config_create, name='config_create'),
    path('email-config/<int:pk>/', views.config_edit, name='config_edit'),
    path('email-config/<int:pk>/delete/', views.config_delete, name='config_delete'),
    path('action/<str:token>/', views.email_action_view, name='email_action'),
    path('email-logs/', views.email_logs, name='email_logs'),
    path('email-logs/<int:pk>/retry/', views.retry_email, name='retry_email'),
    path('email-logs/retry-all/', views.retry_all_failed, name='retry_all_failed'),
    path('send-reminder/<str:req_type>/<int:pk>/', views.send_reminder, name='send_reminder'),
    path('track/<str:req_type>/<int:pk>/', views.track_view, name='track'),
    path('audit-log/', views.audit_log_view, name='audit_log'),
]
