from django.urls import path
from . import views

app_name = 'transport_requisition'

urlpatterns = [
    path('', views.list_view, name='list'),
    path('create/', views.create_view, name='create'),
    path('<int:pk>/', views.detail_view, name='detail'),
    path('<int:pk>/approve/', views.approve_view, name='approve'),
    path('<int:pk>/reject/', views.reject_view, name='reject'),
    path('report/', views.report_view, name='report'),
    path('report/export/', views.export_excel_view, name='export_excel'),
    path('<int:pk>/assign-driver/', views.assign_driver_view, name='assign_driver'),
]
