from django.urls import path
from . import views

app_name = 'ict_requisition'

urlpatterns = [
    path('', views.list_view, name='list'),
    path('create/', views.create_view, name='create'),
    path('<int:pk>/', views.detail_view, name='detail'),
    path('<int:pk>/approve/', views.approve_view, name='approve'),
    path('<int:pk>/reject/', views.reject_view, name='reject'),
]
