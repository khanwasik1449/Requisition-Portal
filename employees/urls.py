from django.urls import path
from . import views

app_name = 'employees'

urlpatterns = [
    path('', views.employee_list, name='employee_list'),
    path('add/', views.add_employee, name='add_employee'),
    path('edit/<int:pk>/', views.edit_employee, name='edit_employee'),
    path('delete/<int:pk>/', views.delete_employee, name='delete_employee'),
    path('import/', views.import_employees, name='import_employees'),
    path('api/<str:pin>/', views.employee_api, name='employee_api'),
    path('detail/<str:pin>/', views.employee_detail, name='employee_detail'),
]